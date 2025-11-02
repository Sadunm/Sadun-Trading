"""
Thread-safe position manager
"""
from threading import Lock
from datetime import datetime
from typing import Dict, List, Optional
from utils.validators import validate_price, validate_quantity, validate_stop_loss_take_profit
from utils.logger import setup_logger

logger = setup_logger("position_manager")


class Position:
    """Represents a trading position"""
    
    def __init__(self, symbol: str, strategy: str, action: str, entry_price: float, 
                 quantity: float, stop_loss: float, take_profit: float):
        # Validate all inputs
        if not validate_price(entry_price):
            raise ValueError(f"Invalid entry price: {entry_price}")
        if not validate_quantity(quantity):
            raise ValueError(f"Invalid quantity: {quantity}")
        
        self.symbol = symbol
        self.strategy = strategy
        self.action = action.upper()  # BUY or SELL
        self.entry_price = entry_price
        self.original_quantity = quantity  # Original full quantity
        self.quantity = quantity  # Current remaining quantity (for partial closes)
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.entry_time = datetime.now()
        self.exit_price = None
        self.exit_time = None
        self.pnl = 0.0
        self.pnl_pct = 0.0
        self.status = 'OPEN'
        self.exit_reason = None
        self.partial_closes = []  # Track partial closes: [{'quantity': float, 'price': float, 'pnl': float, 'reason': str, 'time': datetime}]
        self.total_partial_pnl = 0.0  # Sum of all partial close profits
    
    def partial_close(self, close_quantity: float, exit_price: float, exit_reason: str, fees: float = 0.0) -> Dict:
        """
        Close partial quantity of position
        Returns: {'closed_quantity': float, 'pnl': float, 'remaining_quantity': float, 'is_full_close': bool}
        """
        from utils.validators import safe_divide
        
        if not validate_price(exit_price) or not validate_quantity(close_quantity):
            raise ValueError(f"Invalid price or quantity: price={exit_price}, qty={close_quantity}")
        
        if close_quantity > self.quantity:
            close_quantity = self.quantity  # Clamp to available
        
        # Calculate P&L for this partial close
        if self.action == 'BUY':
            partial_pnl = (exit_price - self.entry_price) * close_quantity - fees
        else:  # SELL
            partial_pnl = (self.entry_price - exit_price) * close_quantity - fees
        
        # Track partial close
        partial_data = {
            'quantity': close_quantity,
            'price': exit_price,
            'pnl': partial_pnl,
            'reason': exit_reason,
            'time': datetime.now(),
            'fees': fees
        }
        self.partial_closes.append(partial_data)
        self.total_partial_pnl += partial_pnl
        
        # Update remaining quantity
        self.quantity -= close_quantity
        
        # Check if fully closed
        is_full_close = (self.quantity <= 0.00000001)  # Small tolerance for floating point
        
        if is_full_close:
            # Fully closed - finalize
            self.exit_price = exit_price
            self.exit_time = datetime.now()
            self.exit_reason = exit_reason
            self.status = 'CLOSED'
            self.quantity = 0.0
            # Total P&L = sum of all partials
            self.pnl = self.total_partial_pnl
            # Calculate overall P&L percentage
            total_value = self.original_quantity * self.entry_price
            self.pnl_pct = safe_divide(self.pnl, total_value, 0.0) * 100.0
        
        return {
            'closed_quantity': close_quantity,
            'pnl': partial_pnl,
            'remaining_quantity': self.quantity,
            'is_full_close': is_full_close,
            'total_pnl': self.total_partial_pnl
        }
    
    def close(self, exit_price: float, exit_reason: str, fees: float = 0.0):
        """Close the FULL remaining position and calculate total P&L"""
        from utils.validators import safe_divide
        
        if not validate_price(exit_price):
            raise ValueError(f"Invalid exit price: {exit_price}")
        
        # If already have partial closes, add this as final partial
        if len(self.partial_closes) > 0:
            # This is closing remaining quantity
            final_close = self.partial_close(self.quantity, exit_price, exit_reason, fees)
            return  # partial_close already finalizes everything
        
        # No partial closes - full close as before
        self.exit_price = exit_price
        self.exit_time = datetime.now()
        self.exit_reason = exit_reason
        self.status = 'CLOSED'
        
        # Calculate P&L
        if self.action == 'BUY':
            self.pnl = (exit_price - self.entry_price) * self.quantity - fees
            self.pnl_pct = safe_divide(
                (exit_price - self.entry_price),
                self.entry_price,
                0.0
            ) * 100
        else:  # SELL
            self.pnl = (self.entry_price - exit_price) * self.quantity - fees
            self.pnl_pct = safe_divide(
                (self.entry_price - exit_price),
                self.entry_price,
                0.0
            ) * 100
        
        self.quantity = 0.0  # Fully closed
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'symbol': self.symbol,
            'strategy': self.strategy,
            'action': self.action,
            'entry_price': self.entry_price,
            'original_quantity': self.original_quantity,
            'quantity': self.quantity,  # Current remaining
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'entry_time': self.entry_time.isoformat(),
            'exit_price': self.exit_price,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'pnl': self.pnl if self.status == 'CLOSED' else self.total_partial_pnl,  # Show partial P&L if open
            'pnl_pct': self.pnl_pct,
            'status': self.status,
            'exit_reason': self.exit_reason,
            'partial_closes': [
                {
                    'quantity': pc['quantity'],
                    'price': pc['price'],
                    'pnl': pc['pnl'],
                    'reason': pc['reason'],
                    'time': pc['time'].isoformat()
                }
                for pc in self.partial_closes
            ],
            'total_partial_pnl': self.total_partial_pnl
        }


class PositionManager:
    """Thread-safe position manager"""
    
    def __init__(self):
        self.positions: Dict[str, Position] = {}  # symbol+strategy as key
        self.lock = Lock()
    
    def open_position(self, symbol: str, strategy: str, action: str, entry_price: float, 
                     quantity: float, stop_loss: float, take_profit: float) -> bool:
        """Open a new position (thread-safe)"""
        try:
            key = f"{symbol}_{strategy}"
            
            with self.lock:
                # Check if already exists
                if key in self.positions:
                    logger.warning(f"[WARN] Position already exists: {key}")
                    return False
                
                # Validate stop loss/take profit
                valid, error = validate_stop_loss_take_profit(entry_price, stop_loss, take_profit, action)
                if not valid:
                    logger.error(f"[ERROR] Invalid stop loss/take profit: {error}")
                    return False
                
                # Create position
                position = Position(
                    symbol=symbol,
                    strategy=strategy,
                    action=action,
                    entry_price=entry_price,
                    quantity=quantity,
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
                
                self.positions[key] = position
                logger.info(f"[OK] Opened {action} position: {symbol} @ ${entry_price:.2f} qty={quantity:.6f}")
                return True
                
        except Exception as e:
            logger.error(f"[ERROR] Error opening position: {e}", exc_info=True)
            return False
    
    def partial_close_position(self, symbol: str, strategy: str, close_quantity: float,
                               exit_price: float, exit_reason: str, fees: float = 0.0) -> Optional[Dict]:
        """Close partial quantity of position (thread-safe)"""
        try:
            key = f"{symbol}_{strategy}"
            
            with self.lock:
                if key not in self.positions:
                    logger.warning(f"[WARN] Position not found: {key}")
                    return None
                
                position = self.positions[key]
                result = position.partial_close(close_quantity, exit_price, exit_reason, fees)
                
                # If fully closed, remove from open positions
                if result['is_full_close']:
                    del self.positions[key]
                    logger.info(f"[OK] Fully closed position: {symbol} Total P&L=${position.pnl:.2f} ({position.pnl_pct:.2f}%)")
                    return {'position': position, **result}
                else:
                    logger.info(f"[PARTIAL] Closed {close_quantity:.6f} of {symbol}: P&L=${result['pnl']:.2f}, Remaining={result['remaining_quantity']:.6f}")
                    return {'position': position, **result}
                
        except Exception as e:
            logger.error(f"[ERROR] Error partial closing position: {e}", exc_info=True)
            return None
    
    def close_position(self, symbol: str, strategy: str, exit_price: float, 
                      exit_reason: str, fees: float = 0.0) -> Optional[Position]:
        """Close FULL remaining position (thread-safe)"""
        try:
            key = f"{symbol}_{strategy}"
            
            with self.lock:
                if key not in self.positions:
                    logger.warning(f"[WARN] Position not found: {key}")
                    return None
                
                position = self.positions[key]
                position.close(exit_price, exit_reason, fees)
                
                # Remove from open positions
                del self.positions[key]
                
                logger.info(f"[OK] Closed position: {symbol} Total P&L=${position.pnl:.2f} ({position.pnl_pct:.2f}%)")
                return position
                
        except Exception as e:
            logger.error(f"[ERROR] Error closing position: {e}", exc_info=True)
            return None
    
    def get_position(self, symbol: str, strategy: str) -> Optional[Position]:
        """Get position by symbol and strategy"""
        key = f"{symbol}_{strategy}"
        with self.lock:
            return self.positions.get(key)
    
    def has_position(self, symbol: str, strategy: Optional[str] = None) -> bool:
        """Check if position exists"""
        with self.lock:
            if strategy:
                key = f"{symbol}_{strategy}"
                return key in self.positions
            else:
                return any(pos.symbol == symbol for pos in self.positions.values())
    
    def get_all_positions(self) -> List[Position]:
        """Get all open positions"""
        with self.lock:
            return list(self.positions.values())
    
    def get_open_positions_count(self) -> int:
        """Get count of open positions"""
        with self.lock:
            return len(self.positions)

