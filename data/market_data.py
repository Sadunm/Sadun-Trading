"""
Market data fetching and caching
"""
import time
from typing import Optional, Tuple, Dict
from core.api_client import BinanceAPIClient
from utils.logger import setup_logger

logger = setup_logger("market_data")


class MarketData:
    """Market data provider with caching"""
    
    def __init__(self, api_client: BinanceAPIClient, cache_duration: int = 5):
        self.api_client = api_client
        self.cache_duration = cache_duration
        
        # Cache
        self._price_cache: Dict[str, Tuple[float, float]] = {}  # symbol -> (price, timestamp)
        self._klines_cache: Dict[str, Tuple[Tuple, float]] = {}  # symbol -> (data, timestamp)
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price with caching"""
        try:
            now = time.time()
            
            # Check cache
            if symbol in self._price_cache:
                cached_price, cache_time = self._price_cache[symbol]
                if now - cache_time < self.cache_duration:
                    return cached_price
            
            # Fetch from API
            price = self.api_client.get_current_price(symbol)
            if price:
                self._price_cache[symbol] = (price, now)
            
            return price
            
        except Exception as e:
            logger.error(f"[ERROR] Error getting current price for {symbol}: {e}")
            return None
    
    def get_klines(self, symbol: str, interval: str = "5m", limit: int = 200) -> Optional[Tuple]:
        """Get klines with caching"""
        try:
            now = time.time()
            cache_key = f"{symbol}_{interval}_{limit}"
            
            # Check cache
            if cache_key in self._klines_cache:
                cached_data, cache_time = self._klines_cache[cache_key]
                if now - cache_time < self.cache_duration:
                    return cached_data
            
            # Fetch from API
            klines = self.api_client.get_klines(symbol, interval, limit)
            if klines:
                self._klines_cache[cache_key] = (klines, now)
            
            return klines
            
        except Exception as e:
            # Filter 400 errors for symbols not available on testnet (silent skip)
            error_str = str(e).lower()
            if '400' in error_str or 'bad request' in error_str:
                logger.debug(f"[SKIP] {symbol} not available on testnet, skipping silently")
                # Cache None to avoid repeated requests
                self._klines_cache[cache_key] = (None, now)
                return None
            logger.error(f"[ERROR] Error getting klines for {symbol}: {e}")
            return None

