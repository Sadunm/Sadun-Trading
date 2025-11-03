"""
Real Bybit/Binance fee calculation - EXACT match to live trading
Default: Bybit (0.055% maker, 0.075% taker - LOWER fees)
"""
from typing import Dict, Any
from utils.validators import validate_price, safe_divide
from utils.logger import setup_logger

logger = setup_logger("fee_calculator")


class FeeCalculator:
    """Calculate REAL Bybit/Binance fees - EXACT match to live trading (Default: Bybit - lower fees)"""
    
    # Exchange fees (updated for Bybit)
    # Bybit Fees (2024-2025) - LOWER than Binance!
    BYBIT_SPOT_MAKER_FEE = 0.00055  # 0.055%
    BYBIT_SPOT_TAKER_FEE = 0.00075  # 0.075%
    
    # Binance Fees (for comparison)
    BINANCE_SPOT_MAKER_FEE = 0.001  # 0.1%
    BINANCE_SPOT_TAKER_FEE = 0.001  # 0.1%
    
    FUTURES_MAKER_FEE = 0.0002  # 0.02%
    FUTURES_TAKER_FEE = 0.0004  # 0.04%
    
    def __init__(self, trading_type: str = 'spot', use_maker: bool = False, exchange: str = 'bybit'):
        """
        Args:
            trading_type: 'spot' or 'futures'
            use_maker: True for limit orders, False for market orders
            exchange: 'bybit' (default, lower fees) or 'binance'
        """
        self.trading_type = trading_type.lower()
        self.use_maker = use_maker
        self.exchange = exchange.lower()
        
        # Set fees based on exchange
        if self.trading_type == 'spot':
            if self.exchange == 'bybit':
                self.maker_fee = self.BYBIT_SPOT_MAKER_FEE  # 0.055%
                self.taker_fee = self.BYBIT_SPOT_TAKER_FEE  # 0.075%
            else:  # binance
                self.maker_fee = self.BINANCE_SPOT_MAKER_FEE  # 0.1%
                self.taker_fee = self.BINANCE_SPOT_TAKER_FEE  # 0.1%
        else:  # futures
            self.maker_fee = self.FUTURES_MAKER_FEE
            self.taker_fee = self.FUTURES_TAKER_FEE
    
    def calculate_entry_fee(self, order_value_usd: float) -> float:
        """Calculate entry fee"""
        try:
            if not validate_price(order_value_usd):
                return 0.0
            
            # Use exchange-specific fees
            fee_rate = self.maker_fee if self.use_maker else self.taker_fee
            
            fee = order_value_usd * fee_rate
            return max(0.0, fee)
            
        except Exception as e:
            logger.error(f"[ERROR] Error calculating entry fee: {e}")
            return 0.0
    
    def calculate_exit_fee(self, order_value_usd: float) -> float:
        """Calculate exit fee"""
        return self.calculate_entry_fee(order_value_usd)
    
    def calculate_round_trip_fee(self, order_value_usd: float) -> float:
        """Calculate total fees for buy + sell"""
        try:
            entry_fee = self.calculate_entry_fee(order_value_usd)
            exit_fee = self.calculate_exit_fee(order_value_usd)
            return entry_fee + exit_fee
        except Exception as e:
            logger.error(f"[ERROR] Error calculating round trip fee: {e}")
            return 0.0
    
    def get_minimum_take_profit_pct(self) -> float:
        """
        Calculate minimum take-profit % to cover fees + profit
        
        Returns: Minimum take-profit percentage
        """
        try:
            # Round trip fee on $100
            round_trip_fee_pct = self.calculate_round_trip_fee(100.0) / 100.0
            
            # Additional costs
            slippage_pct = 0.0003  # 0.03% average (Bybit has slightly better liquidity = similar slippage)
            spread_pct = 0.0005 if self.trading_type == 'spot' else 0.0004  # 0.05% or 0.04%
            
            # Minimum profit margin
            profit_margin_pct = 0.0017  # 0.17% minimum profit (Bybit: lower fees = can aim for slightly higher profit)
            
            # Total minimum
            min_tp_pct = round_trip_fee_pct + slippage_pct + spread_pct + profit_margin_pct
            
            # For spot, ensure minimum (Bybit: 0.13% fees vs Binance 0.20% fees = lower minimum)
            if self.trading_type == 'spot':
                if self.exchange == 'bybit':
                    min_tp_pct = max(min_tp_pct, 0.0035)  # 0.35% minimum for Bybit (lower fees)
                else:
                    min_tp_pct = max(min_tp_pct, 0.0040)  # 0.40% minimum for Binance
            else:  # futures
                min_tp_pct = max(min_tp_pct, 0.0025)  # 0.25% minimum
            
            return min_tp_pct * 100  # Return as percentage
            
        except Exception as e:
            logger.error(f"[ERROR] Error calculating minimum take profit: {e}")
            # Return safe defaults (Bybit: lower fees = lower minimum)
            if self.trading_type == 'spot':
                return 0.35 if self.exchange == 'bybit' else 0.40  # Bybit: 0.35%, Binance: 0.40%
            else:
                return 0.25

