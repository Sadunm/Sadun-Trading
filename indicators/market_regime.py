"""
Market regime detection
"""
from typing import Dict, Any
from utils.logger import setup_logger

logger = setup_logger("market_regime")


class MarketRegimeDetector:
    """Detect market conditions (trending, ranging, volatile)"""
    
    @staticmethod
    def detect_regime(indicators: Dict[str, Any]) -> str:
        """Detect current market regime"""
        try:
            if not indicators:
                return "UNKNOWN"
            
            rsi = indicators.get('rsi', 50.0)
            ema_9 = indicators.get('ema_9', 0.0)
            ema_21 = indicators.get('ema_21', 0.0)
            macd_hist = indicators.get('macd_hist', 0.0)
            atr_pct = indicators.get('atr_pct', 0.0)
            
            # Determine regime
            if ema_9 > ema_21 and macd_hist > 0:
                if rsi > 60:
                    return "STRONG_UPTREND"
                else:
                    return "UPTREND"
            elif ema_9 < ema_21 and macd_hist < 0:
                if rsi < 40:
                    return "STRONG_DOWNTREND"
                else:
                    return "DOWNTREND"
            elif atr_pct > 2.0:
                return "HIGH_VOLATILITY"
            else:
                return "RANGING"
                
        except Exception as e:
            logger.error(f"[ERROR] Error detecting market regime: {e}")
            return "UNKNOWN"

