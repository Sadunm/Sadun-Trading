"""
Base strategy class for all trading strategies
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from utils.validators import clamp_value
from utils.logger import setup_logger

logger = setup_logger("strategies")


class BaseStrategy(ABC):
    """Base class for all trading strategies"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.enabled = config.get('enabled', True)
        self.confidence_threshold = config.get('confidence_threshold', 20.0)
        self.max_hold_time_minutes = config.get('max_hold_time_minutes', 1440)
        self.stop_loss_pct = config.get('stop_loss_pct', 1.0)
        self.take_profit_pct = config.get('take_profit_pct', 2.0)
    
    @abstractmethod
    def generate_signal(
        self,
        symbol: str,
        indicators: Dict[str, Any],
        price: float,
        market_regime: str
    ) -> Optional[Dict[str, Any]]:
        """Generate trading signal - must be implemented"""
        pass
    
    def calculate_confidence(self, indicators: Dict[str, Any], action: str, base: float = 20.0) -> float:
        """Calculate signal confidence (0-100)"""
        try:
            confidence = base
            
            # Add confidence based on indicators
            rsi = indicators.get('rsi', 50.0)
            if action == 'BUY' and rsi < 40:
                confidence += 10
            elif action == 'SELL' and rsi > 60:
                confidence += 10
            
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if volume_ratio > 1.5:
                confidence += 5
            
            macd_hist = indicators.get('macd_hist', 0.0)
            if action == 'BUY' and macd_hist > 0:
                confidence += 5
            elif action == 'SELL' and macd_hist < 0:
                confidence += 5
            
            # Clamp to 0-100
            confidence = clamp_value(confidence, 0.0, 100.0)
            
            return confidence
            
        except Exception as e:
            logger.error(f"[ERROR] Error calculating confidence: {e}")
            return base

