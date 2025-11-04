"""
Base Strategy Class
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from utils.logger import setup_logger

logger = setup_logger("base_strategy")


class BaseStrategy(ABC):
    """Base class for all trading strategies"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.enabled = config.get('enabled', True)
        self.min_confidence = config.get('min_confidence', 0.6)
        self.max_position_pct = config.get('max_position_pct', 0.2)
        
    @abstractmethod
    def generate_signal(
        self,
        symbol: str,
        features: Dict[str, Any],
        current_price: float,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Generate trading signal
        
        Returns:
            {
                'action': 'LONG' or 'SHORT' or 'FLAT',
                'confidence': float (0.0-1.0),
                'entry_price': float,
                'stop_loss': float,
                'take_profit': float,
                'expected_return': float,
                'expected_risk': float,
                'reason': str
            } or None
        """
        pass
    
    def calculate_position_size(
        self,
        signal: Dict[str, Any],
        capital: float,
        risk_per_trade: float = 0.01
    ) -> float:
        """
        Calculate position size based on risk
        
        Args:
            signal: Signal dictionary
            capital: Available capital
            risk_per_trade: Risk per trade (default 1%)
        
        Returns:
            Position size in base currency
        """
        if signal.get('action') == 'FLAT':
            return 0.0
        
        entry_price = signal.get('entry_price', 0)
        stop_loss = signal.get('stop_loss', 0)
        
        if entry_price <= 0 or stop_loss <= 0:
            return 0.0
        
        # Risk amount
        risk_amount = capital * risk_per_trade
        
        # Price risk per unit
        if signal.get('action') == 'LONG':
            price_risk = entry_price - stop_loss
        else:  # SHORT
            price_risk = stop_loss - entry_price
        
        if price_risk <= 0:
            return 0.0
        
        # Position size
        position_size = risk_amount / price_risk
        
        # Apply max position limit
        max_position = capital * self.max_position_pct
        position_size = min(position_size, max_position / entry_price if entry_price > 0 else 0)
        
        return position_size
    
    def validate_signal(self, signal: Dict[str, Any]) -> bool:
        """Validate signal before execution"""
        if not signal:
            return False
        
        # Check required fields
        required = ['action', 'confidence', 'entry_price', 'stop_loss', 'take_profit']
        if not all(key in signal for key in required):
            logger.warning(f"[WARN] Signal missing required fields: {signal}")
            return False
        
        # Check confidence threshold
        if signal.get('confidence', 0) < self.min_confidence:
            return False
        
        # Check action
        if signal.get('action') not in ['LONG', 'SHORT', 'FLAT']:
            return False
        
        # Check prices
        entry = signal.get('entry_price', 0)
        stop = signal.get('stop_loss', 0)
        tp = signal.get('take_profit', 0)
        
        if entry <= 0 or stop <= 0 or tp <= 0:
            return False
        
        # Validate stop loss and take profit
        if signal.get('action') == 'LONG':
            if stop >= entry or tp <= entry:
                return False
        else:  # SHORT
            if stop <= entry or tp >= entry:
                return False
        
        return True

