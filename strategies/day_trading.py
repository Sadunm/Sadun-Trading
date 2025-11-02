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
            
            # IMPROVED: Stricter volume filter - avoid low-volume trades
            if volume_ratio < 1.2:  # Increased from 1.0
                return None
            
            # IMPROVED: BUY signal - stricter EMA crossover + stronger RSI
            if ema_9 > ema_21 and macd_hist > 0.001:  # MACD clearly positive (was just >0)
                # Stricter: RSI should be more oversold, price closer to lower BB
                if rsi < 45 and price <= bb_lower * 1.015:  # RSI <45 (was 50), closer to BB (was 1.02)
                    # Additional momentum check
                    momentum_3 = indicators.get('momentum_3', 0.0)
                    if momentum_3 > 0:  # Positive momentum
                        confidence = self.calculate_confidence(indicators, 'BUY', 28.0)  # Higher base (was 25.0)
                        if confidence >= self.confidence_threshold:
                            logger.info(f"[OK] {symbol} DAY TRADING BUY: RSI={rsi:.1f}, EMA9>EMA21, Conf={confidence:.1f}%")
                            return {
                                'action': 'BUY',
                                'confidence': confidence,
                                'reason': 'Day Trading Strong Uptrend Oversold'
                            }
            
            # IMPROVED: SELL signal - stricter EMA crossover + stronger RSI
            if ema_9 < ema_21 and macd_hist < -0.001:  # MACD clearly negative (was just <0)
                # Stricter: RSI should be more overbought, price closer to upper BB
                if rsi > 55 and price >= bb_upper * 0.985:  # RSI >55 (was 50), closer to BB (was 0.98)
                    # Additional momentum check
                    momentum_3 = indicators.get('momentum_3', 0.0)
                    if momentum_3 < 0:  # Negative momentum
                        confidence = self.calculate_confidence(indicators, 'SELL', 28.0)  # Higher base (was 25.0)
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

