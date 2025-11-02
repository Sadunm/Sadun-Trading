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
            
            # BALANCED: Volume filter - momentum needs volume but not too strict
            if volume_ratio < 1.2:  # Balanced: was 1.1, tried 1.3, balanced at 1.2
                return None
            
            # BALANCED: BUY signal - good momentum but not overly strict
            if momentum_3 > 0.55 and momentum_10 > 0.35 and macd_hist > 0:  # Balanced: momentum (was 0.5/0.3, tried 0.6/0.4), MACD positive (was >0, tried >0.001)
                if rsi < 68:  # Balanced: not too overbought (was 70, tried 65)
                    # Check: momentum indicators aligned (preferred but not required if strong enough)
                    if momentum_3 >= momentum_10 * 0.8:  # Short-term at least 80% of long-term (was strict >)
                        confidence = self.calculate_confidence(indicators, 'BUY', 22.0)  # Balanced base (was 22.0, tried 25.0)
                        if confidence >= self.confidence_threshold:
                            logger.info(f"[OK] {symbol} MOMENTUM BUY: Mom3={momentum_3:.2f}, Mom10={momentum_10:.2f}, Conf={confidence:.1f}%")
                            return {
                                'action': 'BUY',
                                'confidence': confidence,
                                'reason': 'Strong Momentum Uptrend'
                            }
            
            # BALANCED: SELL signal - good momentum but not overly strict
            if momentum_3 < -0.55 and momentum_10 < -0.35 and macd_hist < 0:  # Balanced: momentum (was -0.5/-0.3, tried -0.6/-0.4), MACD negative (was <0, tried <-0.001)
                if rsi > 32:  # Balanced: not too oversold (was 30, tried 35)
                    # Check: momentum indicators aligned (preferred but not required if strong enough)
                    if momentum_3 <= momentum_10 * 0.8:  # Short-term at most 80% of long-term (was strict <)
                        confidence = self.calculate_confidence(indicators, 'SELL', 22.0)  # Balanced base (was 22.0, tried 25.0)
                        if confidence >= self.confidence_threshold:
                            logger.info(f"[OK] {symbol} MOMENTUM SELL: Mom3={momentum_3:.2f}, Mom10={momentum_10:.2f}, Conf={confidence:.1f}%")
                            return {
                                'action': 'SELL',
                                'confidence': confidence,
                                'reason': 'Strong Momentum Downtrend'
                            }
            
            return None
            
        except Exception as e:
            logger.error(f"[ERROR] Error generating momentum signal: {e}")
            return None

