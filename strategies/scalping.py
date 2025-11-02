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
            
            # IMPROVED: Stricter volume filter - need above-average volume
            if volume_ratio < 1.3:  # Increased from 1.2
                return None
            
            # IMPROVED: ATR filter - need adequate volatility for scalping
            if atr_pct < 0.6:  # Increased from 0.5 for better opportunities
                return None
            
            # IMPROVED: BUY signal - more selective oversold bounce
            if rsi < 40 and momentum_3 > 0.15:  # Stricter: RSI <40 (was 45), momentum >0.15 (was 0.1)
                macd_hist = indicators.get('macd_hist', 0.0)
                # Additional filter: MACD should be positive or turning positive
                if macd_hist > -0.001:  # MACD not strongly negative
                    confidence = self.calculate_confidence(indicators, 'BUY', 22.0)  # Higher base
                    if confidence >= self.confidence_threshold:
                        logger.info(f"[OK] {symbol} SCALPING BUY: RSI={rsi:.1f}, Mom={momentum_3:.2f}, Conf={confidence:.1f}%")
                        return {
                            'action': 'BUY',
                            'confidence': confidence,
                            'reason': 'Scalping Strong Oversold Bounce'
                        }
            
            # IMPROVED: SELL signal - more selective overbought pullback
            if rsi > 60 and momentum_3 < -0.15:  # Stricter: RSI >60 (was 55), momentum <-0.15 (was -0.1)
                macd_hist = indicators.get('macd_hist', 0.0)
                # Additional filter: MACD should be negative or turning negative
                if macd_hist < 0.001:  # MACD not strongly positive
                    confidence = self.calculate_confidence(indicators, 'SELL', 22.0)  # Higher base
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

