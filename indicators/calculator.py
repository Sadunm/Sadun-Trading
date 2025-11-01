"""
Technical indicators calculator
"""
import numpy as np
import talib
from typing import List, Dict, Any
from utils.validators import ensure_min_length, safe_divide, safe_mean
from utils.logger import setup_logger

logger = setup_logger("indicators")


class IndicatorCalculator:
    """Calculate technical indicators safely"""
    
    @staticmethod
    def calculate_all(closes: List[float], highs: List[float], lows: List[float], 
                     volumes: List[float], opens: List[float]) -> Dict[str, Any]:
        """Calculate all indicators"""
        try:
            # CRITICAL: Check minimum data length
            if not ensure_min_length(closes, 200):
                logger.warning(f"[WARN] Insufficient data: {len(closes)} < 200")
                return {}
            
            # Convert to numpy arrays
            closes_arr = np.array(closes[-200:], dtype=np.float64)
            highs_arr = np.array(highs[-200:], dtype=np.float64)
            lows_arr = np.array(lows[-200:], dtype=np.float64)
            volumes_arr = np.array(volumes[-200:], dtype=np.float64)
            opens_arr = np.array(opens[-200:], dtype=np.float64) if opens else closes_arr
            
            indicators = {}
            
            # RSI (requires at least 14 periods)
            try:
                if len(closes_arr) >= 14:
                    rsi = talib.RSI(closes_arr, timeperiod=14)
                    indicators['rsi'] = float(rsi[-1]) if len(rsi) > 0 and not np.isnan(rsi[-1]) else 50.0
                else:
                    indicators['rsi'] = 50.0
            except Exception as e:
                logger.debug(f"RSI calculation error: {e}")
                indicators['rsi'] = 50.0
            
            # EMAs
            try:
                if len(closes_arr) >= 9:
                    ema_9 = talib.EMA(closes_arr, timeperiod=9)
                    indicators['ema_9'] = float(ema_9[-1]) if len(ema_9) > 0 and not np.isnan(ema_9[-1]) else float(closes_arr[-1])
                else:
                    indicators['ema_9'] = float(closes_arr[-1])
            except Exception:
                indicators['ema_9'] = float(closes_arr[-1])
            
            try:
                if len(closes_arr) >= 21:
                    ema_21 = talib.EMA(closes_arr, timeperiod=21)
                    indicators['ema_21'] = float(ema_21[-1]) if len(ema_21) > 0 and not np.isnan(ema_21[-1]) else float(closes_arr[-1])
                else:
                    indicators['ema_21'] = float(closes_arr[-1])
            except Exception:
                indicators['ema_21'] = float(closes_arr[-1])
            
            # MACD
            try:
                if len(closes_arr) >= 26:
                    macd, signal, hist = talib.MACD(closes_arr)
                    indicators['macd'] = float(macd[-1]) if len(macd) > 0 and not np.isnan(macd[-1]) else 0.0
                    indicators['macd_signal'] = float(signal[-1]) if len(signal) > 0 and not np.isnan(signal[-1]) else 0.0
                    indicators['macd_hist'] = float(hist[-1]) if len(hist) > 0 and not np.isnan(hist[-1]) else 0.0
                else:
                    indicators['macd'] = 0.0
                    indicators['macd_signal'] = 0.0
                    indicators['macd_hist'] = 0.0
            except Exception:
                indicators['macd'] = 0.0
                indicators['macd_signal'] = 0.0
                indicators['macd_hist'] = 0.0
            
            # Bollinger Bands
            try:
                if len(closes_arr) >= 20:
                    upper, middle, lower = talib.BBANDS(closes_arr, timeperiod=20, nbdevup=2, nbdevdn=2)
                    indicators['bb_upper'] = float(upper[-1]) if len(upper) > 0 and not np.isnan(upper[-1]) else float(closes_arr[-1])
                    indicators['bb_middle'] = float(middle[-1]) if len(middle) > 0 and not np.isnan(middle[-1]) else float(closes_arr[-1])
                    indicators['bb_lower'] = float(lower[-1]) if len(lower) > 0 and not np.isnan(lower[-1]) else float(closes_arr[-1])
                else:
                    indicators['bb_upper'] = float(closes_arr[-1])
                    indicators['bb_middle'] = float(closes_arr[-1])
                    indicators['bb_lower'] = float(closes_arr[-1])
            except Exception:
                indicators['bb_upper'] = float(closes_arr[-1])
                indicators['bb_middle'] = float(closes_arr[-1])
                indicators['bb_lower'] = float(closes_arr[-1])
            
            # ATR
            try:
                if len(highs_arr) >= 14 and len(lows_arr) >= 14:
                    atr = talib.ATR(highs_arr, lows_arr, closes_arr, timeperiod=14)
                    atr_value = float(atr[-1]) if len(atr) > 0 and not np.isnan(atr[-1]) else 0.0
                    indicators['atr'] = atr_value
                    indicators['atr_pct'] = safe_divide(atr_value, closes_arr[-1], 0.0) * 100
                else:
                    indicators['atr'] = 0.0
                    indicators['atr_pct'] = 0.0
            except Exception:
                indicators['atr'] = 0.0
                indicators['atr_pct'] = 0.0
            
            # Volume ratio
            try:
                if len(volumes_arr) >= 20:
                    avg_volume = safe_mean(list(volumes_arr[-20:]), 1.0)
                    current_volume = volumes_arr[-1]
                    indicators['volume_ratio'] = safe_divide(current_volume, avg_volume, 1.0)
                else:
                    indicators['volume_ratio'] = 1.0
            except Exception:
                indicators['volume_ratio'] = 1.0
            
            # Momentum
            try:
                if len(closes_arr) >= 4:
                    momentum_3 = safe_divide(
                        closes_arr[-1] - closes_arr[-4],
                        closes_arr[-4],
                        0.0
                    ) * 100
                    indicators['momentum_3'] = momentum_3
                else:
                    indicators['momentum_3'] = 0.0
                
                if len(closes_arr) >= 11:
                    momentum_10 = safe_divide(
                        closes_arr[-1] - closes_arr[-11],
                        closes_arr[-11],
                        0.0
                    ) * 100
                    indicators['momentum_10'] = momentum_10
                else:
                    indicators['momentum_10'] = 0.0
            except Exception:
                indicators['momentum_3'] = 0.0
                indicators['momentum_10'] = 0.0
            
            return indicators
            
        except Exception as e:
            logger.error(f"[ERROR] Error calculating indicators: {e}", exc_info=True)
            return {}

