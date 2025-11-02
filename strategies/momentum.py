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
            
            # IMPROVED: Stricter volume filter - momentum needs volume
            if volume_ratio < 1.3:  # Increased from 1.1
                return None
            
            # IMPROVED: BUY signal - stronger momentum requirements
            if momentum_3 > 0.6 and momentum_10 > 0.4 and macd_hist > 0.001:  # Stricter: higher momentum (was 0.5/0.3), MACD clearly positive
                if rsi < 65:  # Stricter: not too overbought (was 70)
                    # Additional check: both momentum indicators aligned
                    if momentum_3 > momentum_10:  # Short-term stronger than long-term
                        confidence = self.calculate_confidence(indicators, 'BUY', 25.0)  # Higher base (was 22.0)
                        if confidence >= self.confidence_threshold:
                            logger.info(f"[OK] {symbol} MOMENTUM BUY: Mom3={momentum_3:.2f}, Mom10={momentum_10:.2f}, Conf={confidence:.1f}%")
                            return {
                                'action': 'BUY',
                                'confidence': confidence,
                                'reason': 'Strong Momentum Uptrend'
                            }
            
            # IMPROVED: SELL signal - stronger momentum requirements
            if momentum_3 < -0.6 and momentum_10 < -0.4 and macd_hist < -0.001:  # Stricter: stronger negative momentum (was -0.5/-0.3), MACD clearly negative
                if rsi > 35:  # Stricter: not too oversold (was 30)
                    # Additional check: both momentum indicators aligned
                    if momentum_3 < momentum_10:  # Short-term weaker than long-term
                        confidence = self.calculate_confidence(indicators, 'SELL', 25.0)  # Higher base (was 22.0)
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

