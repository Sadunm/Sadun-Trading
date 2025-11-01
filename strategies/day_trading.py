"""
Day trading strategy
"""
from typing import Dict, Any, Optional
from strategies.base_strategy import BaseStrategy
from utils.logger import setup_logger

logger = setup_logger("day_trading")


class DayTradingStrategy(BaseStrategy):
    """Day trading strategy"""
    
    def generate_signal(
        self,
        symbol: str,
        indicators: Dict[str, Any],
        price: float,
        market_regime: str
    ) -> Optional[Dict[str, Any]]:
        """Generate day trading signal"""
        try:
            if not self.enabled:
                return None
            
            rsi = indicators.get('rsi', 50.0)
            ema_9 = indicators.get('ema_9', 0.0)
            ema_21 = indicators.get('ema_21', 0.0)
            macd_hist = indicators.get('macd_hist', 0.0)
            volume_ratio = indicators.get('volume_ratio', 1.0)
            bb_upper = indicators.get('bb_upper', price)
            bb_lower = indicators.get('bb_lower', price)
            
            # Volume filter
            if volume_ratio < 1.0:
                return None
            
            # BUY signal - EMA crossover + RSI oversold
            if ema_9 > ema_21 and macd_hist > 0:
                if rsi < 50 and price <= bb_lower * 1.02:  # Near lower BB
                    confidence = self.calculate_confidence(indicators, 'BUY', 25.0)
                    if confidence >= self.confidence_threshold:
                        logger.info(f"[OK] {symbol} DAY TRADING BUY: RSI={rsi:.1f}, Conf={confidence:.1f}%")
                        return {
                            'action': 'BUY',
                            'confidence': confidence,
                            'reason': 'Day Trading Uptrend Oversold'
                        }
            
            # SELL signal - EMA crossover + RSI overbought
            if ema_9 < ema_21 and macd_hist < 0:
                if rsi > 50 and price >= bb_upper * 0.98:  # Near upper BB
                    confidence = self.calculate_confidence(indicators, 'SELL', 25.0)
                    if confidence >= self.confidence_threshold:
                        logger.info(f"[OK] {symbol} DAY TRADING SELL: RSI={rsi:.1f}, Conf={confidence:.1f}%")
                        return {
                            'action': 'SELL',
                            'confidence': confidence,
                            'reason': 'Day Trading Downtrend Overbought'
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"[ERROR] Error generating day trading signal: {e}")
            return None

