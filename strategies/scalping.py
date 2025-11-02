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
            
            # RELAXED: Volume filter - relaxed for testnet (which has low volume)
            if volume_ratio < 0.9:  # Relaxed: 1.2x → 0.9x for testnet compatibility
                # Only log occasionally to avoid spam (every 50th check per symbol)
                if not hasattr(self, '_filter_log_count'):
                    self._filter_log_count = {}
                count = self._filter_log_count.get(symbol, 0)
                self._filter_log_count[symbol] = count + 1
                if count % 50 == 0:
                    logger.info(f"[FILTER] {symbol} SCALPING: Volume={volume_ratio:.2f}x < 0.9x threshold")
                return None
            
            # RELAXED: ATR filter - relaxed for low volatility markets
            if atr_pct < 0.3:  # Relaxed: 0.5% → 0.3% for testnet compatibility
                if not hasattr(self, '_filter_log_count'):
                    self._filter_log_count = {}
                count = self._filter_log_count.get(f"{symbol}_atr", 0)
                self._filter_log_count[f"{symbol}_atr"] = count + 1
                if count % 50 == 0:
                    logger.info(f"[FILTER] {symbol} SCALPING: ATR={atr_pct:.2f}% < 0.3% threshold")
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

