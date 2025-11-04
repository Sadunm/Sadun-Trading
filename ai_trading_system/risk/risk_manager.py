"""
Risk Management Module
"""
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from utils.logger import setup_logger

logger = setup_logger("risk_manager")


class RiskManager:
    """Comprehensive risk management"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get('risk', {})
        
        # Risk limits
        self.max_drawdown_pct = self.config.get('max_drawdown_pct', 5.0)
        self.max_daily_loss_pct = self.config.get('max_daily_loss_pct', 2.0)
        self.max_daily_trades = self.config.get('max_daily_trades', 100)
        self.max_position_size_pct = self.config.get('max_position_size_pct', 1.0)
        self.max_portfolio_risk_pct = self.config.get('max_portfolio_risk_pct', 20.0)
        self.volatility_target = self.config.get('volatility_target', 0.15)
        
        # Tracking
        self.initial_capital = 0.0
        self.current_capital = 0.0
        self.peak_capital = 0.0
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.last_reset_date = datetime.now().date()
        
        # Trade history
        self.trade_history = []
        
    def initialize(self, initial_capital: float):
        """Initialize risk manager"""
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.peak_capital = initial_capital
        logger.info(f"[RISK] Risk manager initialized with capital: ${initial_capital:.2f}")
    
    def can_open_position(
        self,
        position_size: float,
        entry_price: float,
        stop_loss: float,
        current_positions: List[Dict[str, Any]]
    ) -> tuple[bool, str]:
        """
        Check if position can be opened
        
        Returns:
            (allowed, reason)
        """
        # Reset daily counters if new day
        self._reset_daily_counters()
        
        # 1. Check daily trade limit
        if self.daily_trades >= self.max_daily_trades:
            return False, f"Daily trade limit reached ({self.max_daily_trades})"
        
        # 2. Check position size limit
        position_value = position_size * entry_price
        position_pct = (position_value / self.current_capital * 100) if self.current_capital > 0 else 0
        
        if position_pct > self.max_position_size_pct * 100:
            return False, f"Position size too large ({position_pct:.2f}% > {self.max_position_size_pct * 100:.2f}%)"
        
        # 3. Check portfolio risk
        total_risk = self._calculate_portfolio_risk(current_positions, position_size, entry_price, stop_loss)
        if total_risk > self.max_portfolio_risk_pct:
            return False, f"Portfolio risk too high ({total_risk:.2f}% > {self.max_portfolio_risk_pct:.2f}%)"
        
        # 4. Check drawdown
        drawdown = self._calculate_drawdown()
        if drawdown > self.max_drawdown_pct:
            return False, f"Max drawdown exceeded ({drawdown:.2f}% > {self.max_drawdown_pct:.2f}%)"
        
        # 5. Check daily loss
        if self.daily_pnl < -self.max_daily_loss_pct * self.current_capital / 100:
            return False, f"Daily loss limit reached ({self.daily_pnl:.2f})"
        
        return True, "OK"
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        action: str,
        atr_pct: float,
        volatility: float
    ) -> float:
        """Calculate stop loss based on ATR and volatility"""
        # Use ATR-based stop loss
        stop_loss_pct = atr_pct * 2.0  # 2x ATR
        
        # Adjust for volatility targeting
        if volatility > 0:
            volatility_ratio = volatility / self.volatility_target
            stop_loss_pct *= volatility_ratio
        
        if action == 'LONG':
            stop_loss = entry_price * (1 - stop_loss_pct / 100)
        else:  # SHORT
            stop_loss = entry_price * (1 + stop_loss_pct / 100)
        
        return stop_loss
    
    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        risk_amount: float
    ) -> float:
        """Calculate position size based on risk"""
        if entry_price <= 0 or stop_loss <= 0:
            return 0.0
        
        price_risk = abs(entry_price - stop_loss)
        if price_risk <= 0:
            return 0.0
        
        position_size = risk_amount / price_risk
        
        # Apply max position size
        max_position_value = self.current_capital * self.max_position_size_pct
        max_position_size = max_position_value / entry_price if entry_price > 0 else 0
        
        return min(position_size, max_position_size)
    
    def record_trade(self, trade: Dict[str, Any]):
        """Record a trade"""
        self.trade_history.append({
            **trade,
            'timestamp': datetime.now().isoformat()
        })
        
        # Update daily counters
        self.daily_trades += 1
        if 'pnl' in trade:
            self.daily_pnl += trade['pnl']
            self.current_capital += trade['pnl']
            
            # Update peak capital
            if self.current_capital > self.peak_capital:
                self.peak_capital = self.current_capital
    
    def _calculate_drawdown(self) -> float:
        """Calculate current drawdown"""
        if self.peak_capital <= 0:
            return 0.0
        
        drawdown = (self.peak_capital - self.current_capital) / self.peak_capital * 100
        return max(0.0, drawdown)
    
    def _calculate_portfolio_risk(
        self,
        current_positions: List[Dict[str, Any]],
        new_position_size: float,
        new_entry_price: float,
        new_stop_loss: float
    ) -> float:
        """Calculate total portfolio risk"""
        total_risk = 0.0
        
        # Risk from existing positions
        for pos in current_positions:
            pos_size = pos.get('position_size', 0)
            pos_entry = pos.get('entry_price', 0)
            pos_stop = pos.get('stop_loss', 0)
            
            if pos_entry > 0:
                pos_value = pos_size * pos_entry
                stop_loss_pct = abs((pos_stop - pos_entry) / pos_entry * 100)
                risk = pos_value * stop_loss_pct / 100
                total_risk += risk
        
        # Risk from new position
        if new_entry_price > 0:
            new_position_value = new_position_size * new_entry_price
            stop_loss_pct = abs((new_stop_loss - new_entry_price) / new_entry_price * 100)
            risk = new_position_value * stop_loss_pct / 100
            total_risk += risk
        
        # Convert to percentage of capital
        if self.current_capital > 0:
            total_risk_pct = (total_risk / self.current_capital) * 100
        else:
            total_risk_pct = 0.0
        
        return total_risk_pct
    
    def _reset_daily_counters(self):
        """Reset daily counters if new day"""
        today = datetime.now().date()
        if today > self.last_reset_date:
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.last_reset_date = today
            logger.info("[RISK] Daily counters reset")
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Get current risk metrics"""
        return {
            'current_capital': self.current_capital,
            'initial_capital': self.initial_capital,
            'peak_capital': self.peak_capital,
            'drawdown_pct': self._calculate_drawdown(),
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades,
            'total_trades': len(self.trade_history),
            'max_drawdown_pct': self.max_drawdown_pct,
            'max_daily_loss_pct': self.max_daily_loss_pct
        }

