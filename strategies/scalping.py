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
            
            # Volume filter
            if volume_ratio < 1.2:
                return None
            
            # ATR filter - need some volatility
            if atr_pct < 0.5:
                return None
            
            # BUY signal - oversold bounce
            if rsi < 45 and momentum_3 > 0.1:
                confidence = self.calculate_confidence(indicators, 'BUY', 20.0)
                if confidence >= self.confidence_threshold:
                    logger.info(f"[OK] {symbol} SCALPING BUY: RSI={rsi:.1f}, Conf={confidence:.1f}%")
                    return {
                        'action': 'BUY',
                        'confidence': confidence,
                        'reason': 'Scalping Oversold Bounce'
                    }
            
            # SELL signal - overbought pullback
            if rsi > 55 and momentum_3 < -0.1:
                confidence = self.calculate_confidence(indicators, 'SELL', 20.0)
                if confidence >= self.confidence_threshold:
                    logger.info(f"[OK] {symbol} SCALPING SELL: RSI={rsi:.1f}, Conf={confidence:.1f}%")
                    return {
                        'action': 'SELL',
                        'confidence': confidence,
                        'reason': 'Scalping Overbought Pullback'
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"[ERROR] Error generating scalping signal: {e}")
            return None

