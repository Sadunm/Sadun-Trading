"""
Technical Indicators and Feature Engineering
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from ..utils.logger import setup_logger

logger = setup_logger("indicators")


class IndicatorCalculator:
    """Calculate all technical indicators"""
    
    @staticmethod
    def calculate_rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate RSI"""
        if len(prices) < period + 1:
            return np.full(len(prices), 50.0)
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = pd.Series(gains).rolling(window=period).mean().values
        avg_loss = pd.Series(losses).rolling(window=period).mean().values
        avg_loss = np.where(avg_loss == 0, 1e-10, avg_loss)  # Avoid division by zero
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        # Fill initial NaN values
        rsi = np.nan_to_num(rsi, nan=50.0)
        
        return rsi
    
    @staticmethod
    def calculate_macd(
        prices: np.ndarray,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Dict[str, np.ndarray]:
        """Calculate MACD"""
        if len(prices) < slow:
            return {
                'macd': np.zeros(len(prices)),
                'signal': np.zeros(len(prices)),
                'histogram': np.zeros(len(prices))
            }
        
        ema_fast = pd.Series(prices).ewm(span=fast, adjust=False).mean().values
        ema_slow = pd.Series(prices).ewm(span=slow, adjust=False).mean().values
        
        macd = ema_fast - ema_slow
        signal_line = pd.Series(macd).ewm(span=signal, adjust=False).mean().values
        histogram = macd - signal_line
        
        return {
            'macd': macd,
            'signal': signal_line,
            'histogram': histogram
        }
    
    @staticmethod
    def calculate_bollinger_bands(
        prices: np.ndarray,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Dict[str, np.ndarray]:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            return {
                'upper': prices,
                'middle': prices,
                'lower': prices
            }
        
        sma = pd.Series(prices).rolling(window=period).mean().values
        std = pd.Series(prices).rolling(window=period).std().values
        
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        
        return {
            'upper': upper,
            'middle': sma,
            'lower': lower
        }
    
    @staticmethod
    def calculate_atr(
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period: int = 14
    ) -> np.ndarray:
        """Calculate Average True Range"""
        if len(high) < period + 1:
            return np.zeros(len(high))
        
        tr1 = high - low
        tr2 = np.abs(high - np.roll(close, 1))
        tr3 = np.abs(low - np.roll(close, 1))
        
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        atr = pd.Series(tr).rolling(window=period).mean().values
        
        return np.nan_to_num(atr, nan=0.0)
    
    @staticmethod
    def calculate_ema(prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate EMA"""
        if len(prices) < period:
            return prices
        
        ema = pd.Series(prices).ewm(span=period, adjust=False).mean().values
        return ema
    
    @staticmethod
    def calculate_sma(prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate SMA"""
        if len(prices) < period:
            return prices
        
        sma = pd.Series(prices).rolling(window=period).mean().values
        return np.nan_to_num(sma, nan=prices[0] if len(prices) > 0 else 0.0)
    
    @staticmethod
    def calculate_volume_ratio(volumes: np.ndarray, period: int = 20) -> np.ndarray:
        """Calculate volume ratio (current / average)"""
        if len(volumes) < period:
            return np.ones(len(volumes))
        
        avg_volume = pd.Series(volumes).rolling(window=period).mean().values
        avg_volume = np.where(avg_volume == 0, 1.0, avg_volume)  # Avoid division by zero
        
        ratio = volumes / avg_volume
        return np.nan_to_num(ratio, nan=1.0)
    
    @staticmethod
    def calculate_zscore(prices: np.ndarray, period: int = 20) -> np.ndarray:
        """Calculate z-score"""
        if len(prices) < period:
            return np.zeros(len(prices))
        
        sma = pd.Series(prices).rolling(window=period).mean().values
        std = pd.Series(prices).rolling(window=period).std().values
        std = np.where(std == 0, 1e-10, std)  # Avoid division by zero
        
        zscore = (prices - sma) / std
        return np.nan_to_num(zscore, nan=0.0)
    
    @staticmethod
    def calculate_momentum(prices: np.ndarray, period: int = 10) -> np.ndarray:
        """Calculate momentum"""
        if len(prices) < period + 1:
            return np.zeros(len(prices))
        
        momentum = (prices - np.roll(prices, period)) / np.roll(prices, period) * 100
        return np.nan_to_num(momentum, nan=0.0)
    
    @staticmethod
    def calculate_returns(prices: np.ndarray, periods: List[int] = [1, 3, 5, 10]) -> Dict[str, np.ndarray]:
        """Calculate returns for multiple periods"""
        returns = {}
        
        for period in periods:
            if len(prices) < period + 1:
                returns[f'return_{period}'] = np.zeros(len(prices))
                continue
            
            ret = (prices - np.roll(prices, period)) / np.roll(prices, period)
            returns[f'return_{period}'] = np.nan_to_num(ret, nan=0.0)
        
        return returns
    
    @staticmethod
    def calculate_volatility(prices: np.ndarray, period: int = 20) -> np.ndarray:
        """Calculate rolling volatility"""
        if len(prices) < period + 1:
            return np.zeros(len(prices))
        
        returns = np.diff(prices) / prices[:-1]
        volatility = pd.Series(returns).rolling(window=period).std().values * np.sqrt(period)
        
        # Pad with first value
        volatility = np.concatenate([[volatility[0] if len(volatility) > 0 else 0.0], volatility])
        
        return np.nan_to_num(volatility, nan=0.0)
    
    @staticmethod
    def build_features(ohlcv_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build all features from OHLCV data"""
        if len(ohlcv_data) < 50:
            logger.warning(f"[WARN] Insufficient data for features: {len(ohlcv_data)} candles")
            return {}
        
        # Extract arrays
        closes = np.array([c['close'] for c in ohlcv_data])
        highs = np.array([c['high'] for c in ohlcv_data])
        lows = np.array([c['low'] for c in ohlcv_data])
        volumes = np.array([c['volume'] for c in ohlcv_data])
        
        features = {}
        
        # Price features
        features['price'] = closes
        features['high'] = highs
        features['low'] = lows
        features['volume'] = volumes
        
        # Returns
        returns = IndicatorCalculator.calculate_returns(closes, [1, 3, 5, 10, 20])
        features.update(returns)
        
        # Indicators
        features['rsi'] = IndicatorCalculator.calculate_rsi(closes)
        features['rsi_14'] = IndicatorCalculator.calculate_rsi(closes, 14)
        features['rsi_7'] = IndicatorCalculator.calculate_rsi(closes, 7)
        
        macd = IndicatorCalculator.calculate_macd(closes)
        features['macd'] = macd['macd']
        features['macd_signal'] = macd['signal']
        features['macd_histogram'] = macd['histogram']
        
        bb = IndicatorCalculator.calculate_bollinger_bands(closes)
        features['bb_upper'] = bb['upper']
        features['bb_middle'] = bb['middle']
        features['bb_lower'] = bb['lower']
        features['bb_width'] = (bb['upper'] - bb['lower']) / bb['middle']
        features['bb_position'] = (closes - bb['lower']) / (bb['upper'] - bb['lower'] + 1e-10)
        
        features['atr'] = IndicatorCalculator.calculate_atr(highs, lows, closes)
        features['atr_pct'] = features['atr'] / closes * 100
        
        # Moving averages
        features['sma_20'] = IndicatorCalculator.calculate_sma(closes, 20)
        features['sma_50'] = IndicatorCalculator.calculate_sma(closes, 50)
        features['ema_9'] = IndicatorCalculator.calculate_ema(closes, 9)
        features['ema_21'] = IndicatorCalculator.calculate_ema(closes, 21)
        features['ema_50'] = IndicatorCalculator.calculate_ema(closes, 50)
        
        # Volume features
        features['volume_ratio'] = IndicatorCalculator.calculate_volume_ratio(volumes)
        features['volume_sma'] = IndicatorCalculator.calculate_sma(volumes, 20)
        
        # Statistical features
        features['zscore'] = IndicatorCalculator.calculate_zscore(closes)
        features['momentum'] = IndicatorCalculator.calculate_momentum(closes)
        features['volatility'] = IndicatorCalculator.calculate_volatility(closes)
        
        # Additional features
        features['price_change'] = np.diff(closes, prepend=closes[0])
        features['price_change_pct'] = features['price_change'] / closes * 100
        
        # High-low spread
        features['hl_spread'] = (highs - lows) / closes * 100
        features['hl_spread_avg'] = IndicatorCalculator.calculate_sma(features['hl_spread'], 20)
        
        # Trend features
        features['trend_sma'] = features['sma_20'] - features['sma_50']
        features['trend_ema'] = features['ema_9'] - features['ema_21']
        
        logger.debug(f"[FEATURES] Built {len(features)} features from {len(ohlcv_data)} candles")
        
        return features

