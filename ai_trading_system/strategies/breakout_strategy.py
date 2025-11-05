"""
Breakout Strategy with ATR and Volatility Expansion
"""
import numpy as np
from typing import Dict, Any, Optional
from .base_strategy import BaseStrategy
from ..features.indicators import IndicatorCalculator
from ..utils.logger import setup_logger

logger = setup_logger("breakout_strategy")


class BreakoutStrategy(BaseStrategy):
    """Breakout strategy using ATR and volatility expansion"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.timeframe = config.get('timeframe', '5m')
        self.atr_multiplier = config.get('atr_multiplier', 2.0)
        
    def generate_signal(
        self,
        symbol: str,
        features: Dict[str, Any],
        current_price: float,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Generate breakout signal"""
        if not self.enabled:
            return None
        
        try:
            # Get indicators
            prices = features.get('price', [])
            highs = features.get('high', [])
            lows = features.get('low', [])
            atr = features.get('atr', [])
            atr_pct = features.get('atr_pct', [])
            volume_ratio = features.get('volume_ratio', [])
            volatility = features.get('volatility', [])
            
            if len(prices) < 20 or len(highs) < 20 or len(lows) < 20:
                logger.warning(f"[WARN] Insufficient data for breakout strategy")
                return None
            
            # Calculate recent high/low (convert to float)
            lookback = min(20, len(highs))
            recent_high = float(max(highs[-lookback:])) if isinstance(highs, (list, np.ndarray)) else float(highs)
            recent_low = float(min(lows[-lookback:])) if isinstance(lows, (list, np.ndarray)) else float(lows)
            
            current_atr = float(atr[-1]) if atr and isinstance(atr, (list, np.ndarray)) else (float(atr) if atr else 0.0)
            current_atr_pct = float(atr_pct[-1]) if atr_pct and isinstance(atr_pct, (list, np.ndarray)) else (float(atr_pct) if atr_pct else 0.5)
            current_vol = float(volume_ratio[-1]) if volume_ratio and isinstance(volume_ratio, (list, np.ndarray)) else (float(volume_ratio) if volume_ratio else 1.0)
            current_volatility = float(volatility[-1]) if volatility and isinstance(volatility, (list, np.ndarray)) else (float(volatility) if volatility else 0.0)
            
            # Volatility expansion check
            if len(volatility) >= 10:
                avg_volatility = float(np.mean(volatility[-10:]))
                vol_expansion = current_volatility > avg_volatility * 1.5
            else:
                vol_expansion = False
            
            # Breakout detection
            action = 'FLAT'
            confidence = 0.0
            reason = ""
            
            # Upper breakout: price breaks above recent high
            breakout_threshold = current_atr * self.atr_multiplier
            if current_price > recent_high + breakout_threshold:
                if current_vol > 1.3 and vol_expansion:
                    action = 'LONG'
                    confidence = min(0.9, 0.6 + (current_price - recent_high) / recent_high * 100 * 10)
                    reason = f"Upper breakout (price: {current_price:.2f} > high: {recent_high:.2f})"
            
            # Lower breakout: price breaks below recent low
            elif current_price < recent_low - breakout_threshold:
                if current_vol > 1.3 and vol_expansion:
                    action = 'SHORT'
                    confidence = min(0.9, 0.6 + (recent_low - current_price) / current_price * 100 * 10)
                    reason = f"Lower breakout (price: {current_price:.2f} < low: {recent_low:.2f})"
            
            if action == 'FLAT' or confidence < self.min_confidence:
                return None
            
            # Calculate stop loss and take profit
            # Stop loss: opposite side of breakout
            # Take profit: 2x the breakout distance
            
            if action == 'LONG':
                # Stop below breakout level
                stop_loss = recent_high - (current_atr * 0.5)
                # Target: breakout distance * 2
                breakout_distance = current_price - recent_high
                take_profit = current_price + breakout_distance * 2
            else:  # SHORT
                # Stop above breakout level
                stop_loss = recent_low + (current_atr * 0.5)
                # Target: breakout distance * 2
                breakout_distance = recent_low - current_price
                take_profit = current_price - abs(breakout_distance) * 2
            
            # Expected return and risk
            expected_return = abs((take_profit - current_price) / current_price * 100)
            expected_risk = abs((stop_loss - current_price) / current_price * 100)
            
            return {
                'action': action,
                'confidence': confidence,
                'entry_price': current_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'expected_return': expected_return,
                'expected_risk': expected_risk,
                'reason': reason
            }
            
        except Exception as e:
            logger.error(f"[ERROR] Error generating breakout signal: {e}")
            return None

