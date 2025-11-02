"""
Scalping strategy for quick profits
"""
from typing import Dict, Any, Optional
from strategies.base_strategy import BaseStrategy
from utils.logger import setup_logger

logger = setup_logger("scalping")


class ScalpingStrategy(BaseStrategy):
    """Scalping strategy for quick profits"""
    
    def generate_signal(
        self,
        symbol: str,
        indicators: Dict[str, Any],
        price: float,
        market_regime: str
    ) -> Optional[Dict[str, Any]]:
        """Generate scalping signal"""
        try:
            if not self.enabled:
                return None
            
            rsi = indicators.get('rsi', 50.0)
            volume_ratio = indicators.get('volume_ratio', 1.0)
            momentum_3 = indicators.get('momentum_3', 0.0)
            atr_pct = indicators.get('atr_pct', 0.0)
            
            # BALANCED: Volume filter - need above-average volume but not too strict
            if volume_ratio < 1.2:  # Balanced: was 1.2, tried 1.3, back to 1.2
                return None
            
            # BALANCED: ATR filter - need some volatility but not too strict
            if atr_pct < 0.5:  # Balanced: was 0.5, tried 0.6, back to 0.5
                return None
            
            # BALANCED: BUY signal - good conditions but not too restrictive
            if rsi < 42 and momentum_3 > 0.12:  # Balanced: RSI <42 (was 45, tried 40), momentum >0.12 (was 0.1, tried 0.15)
                macd_hist = indicators.get('macd_hist', 0.0)
                # MACD filter: should not be strongly negative (but allow more flexibility)
                if macd_hist > -0.002:  # More flexible: was -0.001
                    confidence = self.calculate_confidence(indicators, 'BUY', 20.0)  # Balanced base
                    if confidence >= self.confidence_threshold:
                        logger.info(f"[OK] {symbol} SCALPING BUY: RSI={rsi:.1f}, Mom={momentum_3:.2f}, Conf={confidence:.1f}%")
                        return {
                            'action': 'BUY',
                            'confidence': confidence,
                            'reason': 'Scalping Strong Oversold Bounce'
                        }
            
            # BALANCED: SELL signal - good conditions but not too restrictive
            if rsi > 58 and momentum_3 < -0.12:  # Balanced: RSI >58 (was 55, tried 60), momentum <-0.12 (was -0.1, tried -0.15)
                macd_hist = indicators.get('macd_hist', 0.0)
                # MACD filter: should not be strongly positive (but allow more flexibility)
                if macd_hist < 0.002:  # More flexible: was 0.001
                    confidence = self.calculate_confidence(indicators, 'SELL', 20.0)  # Balanced base
                    if confidence >= self.confidence_threshold:
                        logger.info(f"[OK] {symbol} SCALPING SELL: RSI={rsi:.1f}, Mom={momentum_3:.2f}, Conf={confidence:.1f}%")
                        return {
                            'action': 'SELL',
                            'confidence': confidence,
                            'reason': 'Scalping Strong Overbought Pullback'
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"[ERROR] Error generating scalping signal: {e}")
            return None

