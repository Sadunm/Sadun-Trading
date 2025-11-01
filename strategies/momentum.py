"""
Momentum trading strategy
"""
from typing import Dict, Any, Optional
from strategies.base_strategy import BaseStrategy
from utils.logger import setup_logger

logger = setup_logger("momentum")


class MomentumStrategy(BaseStrategy):
    """Momentum trading strategy"""
    
    def generate_signal(
        self,
        symbol: str,
        indicators: Dict[str, Any],
        price: float,
        market_regime: str
    ) -> Optional[Dict[str, Any]]:
        """Generate momentum signal"""
        try:
            if not self.enabled:
                return None
            
            momentum_3 = indicators.get('momentum_3', 0.0)
            momentum_10 = indicators.get('momentum_10', 0.0)
            rsi = indicators.get('rsi', 50.0)
            volume_ratio = indicators.get('volume_ratio', 1.0)
            macd_hist = indicators.get('macd_hist', 0.0)
            
            # Volume filter
            if volume_ratio < 1.1:
                return None
            
            # BUY signal - Strong momentum up
            if momentum_3 > 0.5 and momentum_10 > 0.3 and macd_hist > 0:
                if rsi < 70:  # Not too overbought
                    confidence = self.calculate_confidence(indicators, 'BUY', 22.0)
                    if confidence >= self.confidence_threshold:
                        logger.info(f"[OK] {symbol} MOMENTUM BUY: Mom3={momentum_3:.2f}, Conf={confidence:.1f}%")
                        return {
                            'action': 'BUY',
                            'confidence': confidence,
                            'reason': 'Momentum Uptrend'
                        }
            
            # SELL signal - Strong momentum down
            if momentum_3 < -0.5 and momentum_10 < -0.3 and macd_hist < 0:
                if rsi > 30:  # Not too oversold
                    confidence = self.calculate_confidence(indicators, 'SELL', 22.0)
                    if confidence >= self.confidence_threshold:
                        logger.info(f"[OK] {symbol} MOMENTUM SELL: Mom3={momentum_3:.2f}, Conf={confidence:.1f}%")
                        return {
                            'action': 'SELL',
                            'confidence': confidence,
                            'reason': 'Momentum Downtrend'
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"[ERROR] Error generating momentum signal: {e}")
            return None

