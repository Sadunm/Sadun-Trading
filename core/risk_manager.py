"""
Risk management and position sizing
"""
from typing import Tuple, Optional, Dict, Any
from datetime import datetime
from utils.validators import validate_price, safe_divide, clamp_value, validate_stop_loss_take_profit
from utils.logger import setup_logger

logger = setup_logger("risk_manager")


class RiskManager:
    """Manage trading risk and position sizing"""
    
    def __init__(self, config: Dict[str, Any]):
        self.max_position_size_pct = config.get('max_position_size_pct', 2.0)
        self.max_total_positions = config.get('max_total_positions', 5)
        self.max_daily_trades = config.get('max_daily_trades', 20)
        self.max_daily_loss_pct = config.get('max_daily_loss_pct', 2.0)
        self.max_drawdown_pct = config.get('max_drawdown_pct', 5.0)
        self.stop_loss_pct = config.get('stop_loss_pct', 1.0)
        self.take_profit_pct = config.get('take_profit_pct', 2.0)
        self.base_position_size_pct = config.get('base_position_size_pct', 1.0)
        self.min_position_size_usd = config.get('min_position_size_usd', 10.0)
        self.max_position_size_usd = config.get('max_position_size_usd', 200.0)
        
        # Tracking
        self.initial_capital = 0.0
        self.current_capital = 0.0
        self.peak_capital = 0.0
        self.daily_trades_count = 0
        self.daily_pnl = 0.0
        self.last_reset_date = ""
    
    def set_capital(self, initial: float, current: float):
        """Set capital values"""
        self.initial_capital = initial
        self.current_capital = current
        if self.peak_capital == 0.0:
            self.peak_capital = current
        if current > self.peak_capital:
            self.peak_capital = current
    
    def reset_daily_stats(self):
        """Reset daily statistics"""
        today = datetime.now().strftime('%Y-%m-%d')
        if today != self.last_reset_date:
            self.daily_trades_count = 0
            self.daily_pnl = 0.0
            self.last_reset_date = today
    
    def record_trade(self, pnl: float):
        """Record a completed trade"""
        self.daily_trades_count += 1
        self.daily_pnl += pnl
    
    def can_trade(self) -> Tuple[bool, str]:
        """Check if trading is allowed"""
        self.reset_daily_stats()
        
        # Check daily trade limit
        if self.daily_trades_count >= self.max_daily_trades:
            return False, f"Daily trade limit reached ({self.max_daily_trades})"
        
        # Check daily loss limit
        if self.initial_capital > 0:
            daily_loss_pct = safe_divide(
                -self.daily_pnl,
                self.initial_capital,
                0.0
            ) * 100
            
            if daily_loss_pct >= self.max_daily_loss_pct:
                return False, f"Daily loss limit reached ({daily_loss_pct:.2f}%)"
        
        # Check drawdown
        if self.peak_capital > 0:
            drawdown_pct = safe_divide(
                self.peak_capital - self.current_capital,
                self.peak_capital,
                0.0
            ) * 100
            
            if drawdown_pct >= self.max_drawdown_pct:
                return False, f"Max drawdown reached ({drawdown_pct:.2f}%)"
        
        return True, "OK"
    
    def can_open_position(self, current_positions_count: int) -> Tuple[bool, str]:
        """Check if new position can be opened"""
        if current_positions_count >= self.max_total_positions:
            return False, f"Max positions reached ({current_positions_count}/{self.max_total_positions})"
        
        return self.can_trade()
    
    def calculate_position_size(self, entry_price: float, confidence: float = 100.0) -> float:
        """Calculate position size based on risk"""
        try:
            if not validate_price(entry_price):
                return 0.0
            
            # Clamp confidence
            confidence = clamp_value(confidence, 0.0, 100.0)
            
            # Calculate size percentage
            size_pct = self.base_position_size_pct * (confidence / 100.0)
            size_pct = min(size_pct, self.max_position_size_pct)
            
            # Calculate position value
            position_value_usd = safe_divide(
                self.current_capital * size_pct,
                100.0,
                0.0
            )
            
            # Clamp to min/max
            position_value_usd = clamp_value(
                position_value_usd,
                self.min_position_size_usd,
                self.max_position_size_usd
            )
            
            # Calculate quantity
            quantity = safe_divide(position_value_usd, entry_price, 0.0)
            
            return quantity
            
        except Exception as e:
            logger.error(f"[ERROR] Error calculating position size: {e}")
            return 0.0
    
    def calculate_stop_loss(self, entry_price: float, action: str, custom_pct: Optional[float] = None, 
                           add_buffer: bool = True) -> float:
        """
        Calculate stop loss price
        
        Args:
            entry_price: Entry price (already includes slippage/spread)
            action: 'BUY' or 'SELL'
            custom_pct: Custom stop loss percentage
            add_buffer: Add buffer for exit slippage/spread (default: True)
                       Buffer: ~0.08% for spread + slippage on exit
        """
        try:
            if not validate_price(entry_price):
                raise ValueError(f"Invalid entry price: {entry_price}")
            
            stop_loss_pct = custom_pct if custom_pct is not None else self.stop_loss_pct
            
            # Add buffer for exit slippage/spread to prevent instant stop loss hits
            # Exit will also have slippage/spread, so we need extra room
            buffer_pct = 0.08 if add_buffer else 0.0  # ~0.03% spread + ~0.05% slippage
            effective_sl_pct = stop_loss_pct + buffer_pct
            
            if action.upper() == 'BUY':
                stop_loss = entry_price * (1 - effective_sl_pct / 100.0)
            else:  # SELL
                stop_loss = entry_price * (1 + effective_sl_pct / 100.0)
            
            return stop_loss
            
        except Exception as e:
            logger.error(f"[ERROR] Error calculating stop loss: {e}")
            return entry_price
    
    def calculate_take_profit(self, entry_price: float, action: str, custom_pct: Optional[float] = None) -> float:
        """Calculate take profit price"""
        try:
            if not validate_price(entry_price):
                raise ValueError(f"Invalid entry price: {entry_price}")
            
            take_profit_pct = custom_pct if custom_pct is not None else self.take_profit_pct
            
            if action.upper() == 'BUY':
                take_profit = entry_price * (1 + take_profit_pct / 100.0)
            else:  # SELL
                take_profit = entry_price * (1 - take_profit_pct / 100.0)
            
            return take_profit
            
        except Exception as e:
            logger.error(f"[ERROR] Error calculating take profit: {e}")
            return entry_price
    
    def validate_stop_loss_take_profit(
        self,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        action: str
    ) -> Tuple[bool, Optional[str]]:
        """Validate stop loss and take profit are correct"""
        return validate_stop_loss_take_profit(entry_price, stop_loss, take_profit, action)

