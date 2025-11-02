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
            
            # RELAXED: Volume filter - relaxed for testnet (which has low volume)
            if volume_ratio < 0.85:  # Relaxed: 1.1x → 0.85x for testnet compatibility
                return None
            
            # BALANCED: BUY signal - good conditions but not overly strict
            if ema_9 > ema_21 and macd_hist > 0:  # Balanced: MACD positive (was >0, tried >0.001)
                # Balanced: RSI oversold but not too strict, price near lower BB
                if rsi < 48 and price <= bb_lower * 1.02:  # RSI <48 (was 50, tried 45), BB tolerance (was 1.02, tried 1.015)
                    # Momentum check (more flexible)
                    momentum_3 = indicators.get('momentum_3', 0.0)
                    if momentum_3 > -0.05:  # Allow slightly negative momentum (was >0)
                        confidence = self.calculate_confidence(indicators, 'BUY', 25.0)  # Balanced base (was 25.0, tried 28.0)
                        if confidence >= self.confidence_threshold:
                            logger.info(f"[OK] {symbol} DAY TRADING BUY: RSI={rsi:.1f}, EMA9>EMA21, Conf={confidence:.1f}%")
                            return {
                                'action': 'BUY',
                                'confidence': confidence,
                                'reason': 'Day Trading Strong Uptrend Oversold'
                            }
            
            # BALANCED: SELL signal - good conditions but not overly strict
            if ema_9 < ema_21 and macd_hist < 0:  # Balanced: MACD negative (was <0, tried <-0.001)
                # Balanced: RSI overbought but not too strict, price near upper BB
                if rsi > 52 and price >= bb_upper * 0.98:  # RSI >52 (was 50, tried 55), BB tolerance (was 0.98, tried 0.985)
                    # Momentum check (more flexible)
                    momentum_3 = indicators.get('momentum_3', 0.0)
                    if momentum_3 < 0.05:  # Allow slightly positive momentum (was <0)
                        confidence = self.calculate_confidence(indicators, 'SELL', 25.0)  # Balanced base (was 25.0, tried 28.0)
                        if confidence >= self.confidence_threshold:
                            logger.info(f"[OK] {symbol} DAY TRADING SELL: RSI={rsi:.1f}, EMA9<EMA21, Conf={confidence:.1f}%")
                            return {
                                'action': 'SELL',
                                'confidence': confidence,
                                'reason': 'Day Trading Strong Downtrend Overbought'
                            }
            
            return None
            
        except Exception as e:
            logger.error(f"[ERROR] Error generating day trading signal: {e}")
            return None

