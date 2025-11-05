"""
Data Manager - Handles all data operations
"""
import asyncio
import json
import os
import requests
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from .websocket_client import MarketDataStream
from ..utils.logger import setup_logger

logger = setup_logger("data_manager")


class DataManager:
    """Manages all market data operations"""
    
    def __init__(
        self,
        exchange: str,
        symbols: List[str],
        websocket_url: Optional[str] = None,
        store_local: bool = True,
        data_dir: str = "ai_trading_system/data/storage"
    ):
        self.exchange = exchange
        self.symbols = symbols
        self.store_local = store_local
        self.data_dir = Path(data_dir)
        
        # Create data directory
        if self.store_local:
            self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Market data stream
        self.market_stream = MarketDataStream(
            exchange=exchange,
            symbols=symbols,
            url=websocket_url
        )
        
        # Historical data cache
        self.historical_cache = {}
        
        # REST API base URL for fetching historical data
        if exchange.lower() == "bybit":
            self.api_base = "https://api-testnet.bybit.com" if "testnet" in str(websocket_url).lower() else "https://api.bybit.com"
        elif exchange.lower() == "binance":
            self.api_base = "https://testnet.binance.vision" if "testnet" in str(websocket_url).lower() else "https://api.binance.com"
        else:
            self.api_base = None
    
    async def _fetch_historical_klines(self, symbol: str, limit: int = 200, interval: str = "5m") -> List[Dict[str, Any]]:
        """Fetch historical kline data from REST API"""
        if not self.api_base:
            return []
        
        try:
            if self.exchange.lower() == "bybit":
                # Bybit format
                url = f"{self.api_base}/v5/market/kline"
                params = {
                    "category": "spot",
                    "symbol": symbol,
                    "interval": interval.replace("m", ""),  # "5m" -> "5"
                    "limit": limit
                }
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if data.get("retCode") != 0:
                    logger.warning(f"[WARN] Bybit API error: {data.get('retMsg', 'Unknown error')}")
                    return []
                
                klines = data.get("result", {}).get("list", [])
                
                # Convert to standard format [timestamp, open, high, low, close, volume]
                formatted = []
                for k in reversed(klines):  # Reverse to get chronological order
                    formatted.append({
                        'timestamp': int(k[0]),  # startTime
                        'open': float(k[1]),
                        'high': float(k[2]),
                        'low': float(k[3]),
                        'close': float(k[4]),
                        'volume': float(k[5])
                    })
                
            elif self.exchange.lower() == "binance":
                # Binance format (matching existing bot)
                url = f"{self.api_base}/api/v3/klines"
                params = {
                    "symbol": symbol,
                    "interval": interval,  # "5m"
                    "limit": limit
                }
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                klines = response.json()
                
                # Binance format: [Open time, Open, High, Low, Close, Volume, ...]
                formatted = []
                for k in klines:
                    formatted.append({
                        'timestamp': int(k[0]),  # Open time
                        'open': float(k[1]),
                        'high': float(k[2]),
                        'low': float(k[3]),
                        'close': float(k[4]),
                        'volume': float(k[5])
                    })
            
            else:
                logger.warning(f"[WARN] Unsupported exchange: {self.exchange}")
                return []
            
            logger.info(f"[DATA] Fetched {len(formatted)} historical candles for {symbol} from {self.exchange}")
            return formatted
            
        except requests.exceptions.HTTPError as e:
            # Handle different HTTP errors gracefully
            status_code = e.response.status_code if e.response else 0
            if status_code == 400:
                logger.debug(f"[SKIP] {symbol} not available on testnet")
                return []
            elif status_code in [502, 503, 504]:
                # Server errors - testnet might be down
                logger.warning(f"[WARN] Binance testnet server error ({status_code}) for {symbol} - will continue without historical data")
                return []
            elif status_code == 429:
                # Rate limit
                logger.warning(f"[WARN] Rate limit for {symbol} - will continue without historical data")
                return []
            logger.error(f"[ERROR] HTTP error fetching {symbol}: {e}")
            return []
        except requests.exceptions.RequestException as e:
            # Network errors
            logger.warning(f"[WARN] Network error fetching {symbol}: {e} - will continue without historical data")
            return []
        except Exception as e:
            logger.error(f"[ERROR] Failed to fetch historical data for {symbol}: {e}")
            return []
    
    async def start(self):
        """Start data manager"""
        await self.market_stream.start()
        
        # Fetch initial historical data to bootstrap
        logger.info("[DATA] Fetching initial historical data...")
        interval = "5m"  # Standard interval format
        successful = 0
        failed = 0
        
        for symbol in self.symbols:
            historical = await self._fetch_historical_klines(symbol, limit=200, interval=interval)
            if historical:
                # Inject into market stream
                if symbol not in self.market_stream.ohlcv_data:
                    self.market_stream.ohlcv_data[symbol] = []
                self.market_stream.ohlcv_data[symbol] = historical
                logger.info(f"[DATA] Bootstrapped {len(historical)} candles for {symbol}")
                successful += 1
            else:
                failed += 1
                # Small delay to avoid rate limits
                await asyncio.sleep(0.5)
        
        if successful > 0:
            logger.info(f"[DATA] Successfully fetched historical data for {successful}/{len(self.symbols)} symbols")
        if failed > 0:
            logger.warning(f"[WARN] Failed to fetch historical data for {failed} symbols - will rely on WebSocket only")
        
        logger.info("[DATA] Data manager started")
    
    async def stop(self):
        """Stop data manager"""
        await self.market_stream.stop()
        logger.info("[DATA] Data manager stopped")
    
    def get_ohlcv(self, symbol: str, limit: int = 200) -> List[Dict[str, Any]]:
        """Get OHLCV data"""
        return self.market_stream.get_latest_ohlcv(symbol, limit)
    
    def get_orderbook(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get orderbook data"""
        return self.market_stream.get_orderbook(symbol)
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price from latest candle"""
        ohlcv = self.get_ohlcv(symbol, limit=1)
        if ohlcv:
            return ohlcv[-1]['close']
        return None
    
    def save_data(self, symbol: str, data_type: str, data: Any):
        """Save data locally"""
        if not self.store_local:
            return
        
        try:
            filename = self.data_dir / f"{symbol}_{data_type}_{datetime.now().strftime('%Y%m%d')}.json"
            
            # Load existing data
            if filename.exists():
                with open(filename, 'r') as f:
                    existing = json.load(f)
            else:
                existing = []
            
            # Append new data
            existing.append({
                'timestamp': datetime.now().isoformat(),
                'data': data
            })
            
            # Keep only last 1000 entries
            if len(existing) > 1000:
                existing = existing[-1000:]
            
            # Save
            with open(filename, 'w') as f:
                json.dump(existing, f, indent=2)
                
        except Exception as e:
            logger.error(f"[ERROR] Error saving data: {e}")
    
    def load_historical(self, symbol: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Load historical data from local storage"""
        if not self.store_local:
            return []
        
        try:
            data_files = list(self.data_dir.glob(f"{symbol}_*_*.json"))
            historical = []
            
            for file in data_files:
                with open(file, 'r') as f:
                    file_data = json.load(f)
                    historical.extend(file_data)
            
            # Filter by date range
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            
            filtered = [
                entry for entry in historical
                if start <= datetime.fromisoformat(entry['timestamp']) <= end
            ]
            
            return filtered
        except Exception as e:
            logger.error(f"[ERROR] Error loading historical data: {e}")
            return []

