"""
Order Execution Engine with TWAP/VWAP Slicing
"""
import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from utils.logger import setup_logger

logger = setup_logger("order_executor")


class OrderExecutor:
    """Order execution engine with slicing and idempotency"""
    
    def __init__(self, config: Dict[str, Any], api_client):
        self.config = config.get('execution', {})
        self.api_client = api_client
        
        # Execution settings
        self.order_slicing = self.config.get('order_slicing', 'TWAP')
        self.slice_duration = self.config.get('slice_duration_seconds', 60)
        self.max_slippage_pct = self.config.get('max_slippage_pct', 0.1)
        self.min_spread_pct = self.config.get('min_spread_pct', 0.02)
        self.order_idempotency = self.config.get('order_idempotency', True)
        self.retry_failed_orders = self.config.get('retry_failed_orders', True)
        self.max_retries = self.config.get('max_retries', 3)
        
        # Order tracking
        self.pending_orders = {}  # {order_id: order_info}
        self.executed_orders = []  # List of executed orders
        self.order_ids = set()  # For idempotency
        
    async def execute_order(
        self,
        symbol: str,
        action: str,
        quantity: float,
        entry_price: float,
        order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute order with slicing
        
        Args:
            symbol: Trading symbol
            action: 'BUY' or 'SELL'
            quantity: Order quantity
            entry_price: Target entry price
            order_id: Optional order ID for idempotency
        
        Returns:
            Execution result
        """
        # Check idempotency
        if self.order_idempotency and order_id:
            if order_id in self.order_ids:
                logger.warning(f"[WARN] Duplicate order ID: {order_id}")
                return {
                    'success': False,
                    'error': 'Duplicate order ID',
                    'order_id': order_id
                }
            self.order_ids.add(order_id)
        
        # Check spread
        spread_ok = await self._check_spread(symbol)
        if not spread_ok:
            return {
                'success': False,
                'error': 'Spread too wide',
                'symbol': symbol
            }
        
        # Execute with slicing
        if self.order_slicing == 'TWAP':
            result = await self._execute_twap(symbol, action, quantity, entry_price, order_id)
        elif self.order_slicing == 'VWAP':
            result = await self._execute_vwap(symbol, action, quantity, entry_price, order_id)
        else:
            # No slicing
            result = await self._execute_market_order(symbol, action, quantity, entry_price, order_id)
        
        return result
    
    async def _execute_twap(
        self,
        symbol: str,
        action: str,
        total_quantity: float,
        target_price: float,
        order_id: Optional[str]
    ) -> Dict[str, Any]:
        """Execute order using TWAP (Time-Weighted Average Price)"""
        num_slices = max(1, int(self.slice_duration / 10))  # Slice every 10 seconds
        slice_quantity = total_quantity / num_slices
        slice_interval = self.slice_duration / num_slices
        
        executed_quantity = 0.0
        executed_price = 0.0
        executed_slices = []
        
        logger.info(f"[EXEC] Executing TWAP order: {symbol} {action} {total_quantity} in {num_slices} slices")
        
        for i in range(num_slices):
            try:
                # Execute slice
                slice_result = await self._execute_market_order(
                    symbol=symbol,
                    action=action,
                    quantity=slice_quantity,
                    entry_price=target_price,
                    order_id=f"{order_id}_slice_{i}" if order_id else None
                )
                
                if slice_result.get('success'):
                    executed_quantity += slice_result.get('executed_quantity', 0)
                    executed_price += slice_result.get('executed_price', 0) * slice_result.get('executed_quantity', 0)
                    executed_slices.append(slice_result)
                else:
                    logger.warning(f"[WARN] Slice {i} failed: {slice_result.get('error')}")
                
                # Wait before next slice (except last slice)
                if i < num_slices - 1:
                    await asyncio.sleep(slice_interval)
                    
            except Exception as e:
                logger.error(f"[ERROR] Error executing slice {i}: {e}")
                continue
        
        # Calculate average price
        if executed_quantity > 0:
            avg_price = executed_price / executed_quantity
        else:
            avg_price = target_price
        
        return {
            'success': executed_quantity > 0,
            'executed_quantity': executed_quantity,
            'executed_price': avg_price,
            'target_price': target_price,
            'slippage_pct': abs((avg_price - target_price) / target_price * 100) if target_price > 0 else 0,
            'slices': executed_slices,
            'order_id': order_id
        }
    
    async def _execute_vwap(
        self,
        symbol: str,
        action: str,
        total_quantity: float,
        target_price: float,
        order_id: Optional[str]
    ) -> Dict[str, Any]:
        """Execute order using VWAP (Volume-Weighted Average Price)"""
        # Simplified VWAP - similar to TWAP but with volume consideration
        # In production, use actual orderbook volume data
        return await self._execute_twap(symbol, action, total_quantity, target_price, order_id)
    
    async def _execute_market_order(
        self,
        symbol: str,
        action: str,
        quantity: float,
        entry_price: float,
        order_id: Optional[str]
    ) -> Dict[str, Any]:
        """Execute single market order"""
        try:
            # Get current price
            current_price = await self._get_current_price(symbol)
            if not current_price:
                return {
                    'success': False,
                    'error': 'Could not get current price',
                    'symbol': symbol
                }
            
            # Check slippage
            slippage_pct = abs((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
            if slippage_pct > self.max_slippage_pct:
                return {
                    'success': False,
                    'error': f'Slippage too high ({slippage_pct:.2f}% > {self.max_slippage_pct:.2f}%)',
                    'slippage_pct': slippage_pct
                }
            
            # Place order via API client
            if self.api_client:
                order_result = await self.api_client.place_order(
                    symbol=symbol,
                    side=action,
                    quantity=quantity,
                    order_type='MARKET'
                )
                
                if order_result and order_result.get('success'):
                    executed_price = order_result.get('price', current_price)
                    executed_quantity = order_result.get('quantity', quantity)
                    
                    return {
                        'success': True,
                        'executed_quantity': executed_quantity,
                        'executed_price': executed_price,
                        'target_price': entry_price,
                        'slippage_pct': slippage_pct,
                        'order_id': order_id or order_result.get('order_id')
                    }
                else:
                    return {
                        'success': False,
                        'error': order_result.get('error', 'Order failed') if order_result else 'No result',
                        'order_id': order_id
                    }
            else:
                # Paper trading - simulate execution
                return {
                    'success': True,
                    'executed_quantity': quantity,
                    'executed_price': current_price,
                    'target_price': entry_price,
                    'slippage_pct': slippage_pct,
                    'order_id': order_id,
                    'paper_trading': True
                }
                
        except Exception as e:
            logger.error(f"[ERROR] Error executing market order: {e}")
            return {
                'success': False,
                'error': str(e),
                'order_id': order_id
            }
    
    async def _check_spread(self, symbol: str) -> bool:
        """Check if spread is acceptable"""
        try:
            # Get orderbook
            orderbook = await self.api_client.get_orderbook(symbol) if self.api_client else None
            
            if orderbook:
                bids = orderbook.get('bids', [])
                asks = orderbook.get('asks', [])
                
                if bids and asks:
                    bid_price = float(bids[0][0])
                    ask_price = float(asks[0][0])
                    spread_pct = ((ask_price - bid_price) / bid_price * 100) if bid_price > 0 else 0
                    
                    return spread_pct <= self.min_spread_pct
            else:
                # Paper trading - assume spread is OK
                return True
                
        except Exception as e:
            logger.error(f"[ERROR] Error checking spread: {e}")
            return True  # Allow if check fails
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price"""
        try:
            if self.api_client:
                price = await self.api_client.get_current_price(symbol)
                return price
            return None
        except Exception as e:
            logger.error(f"[ERROR] Error getting current price: {e}")
            return None
    
    def generate_order_id(self, symbol: str, action: str, timestamp: float) -> str:
        """Generate unique order ID"""
        return f"{symbol}_{action}_{int(timestamp)}_{int(time.time() * 1000) % 10000}"

