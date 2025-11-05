"""
WebSocket Client for Real-Time Market Data
"""
import asyncio
import json
import websockets
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime
import time
from ..utils.logger import setup_logger

logger = setup_logger("websocket_client")


class WebSocketClient:
    """Async WebSocket client for market data"""
    
    def __init__(
        self,
        url: str,
        symbols: List[str],
        callback: Optional[Callable] = None,
        reconnect_delay: float = 5.0,
        max_reconnect_attempts: int = 10
    ):
        self.url = url
        self.symbols = symbols
        self.callback = callback
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts
        self.websocket = None
        self.running = False
        self.reconnect_attempts = 0
        self.last_message_time = None
        
    async def connect(self):
        """Connect to WebSocket"""
        try:
            self.websocket = await websockets.connect(self.url)
            self.reconnect_attempts = 0
            self.last_message_time = time.time()
            logger.info(f"[WEBSOCKET] Connected to {self.url}")
            return True
        except Exception as e:
            logger.error(f"[ERROR] WebSocket connection failed: {e}")
            return False
    
    async def subscribe(self, channels: List[str]):
        """Subscribe to channels"""
        if not self.websocket:
            await self.connect()
        
        try:
            # Format depends on exchange
            if "bybit" in self.url.lower():
                # Bybit format
                subscribe_msg = {
                    "op": "subscribe",
                    "args": channels
                }
            else:
                # Binance format
                subscribe_msg = {
                    "method": "SUBSCRIBE",
                    "params": channels,
                    "id": 1
                }
            
            await self.websocket.send(json.dumps(subscribe_msg))
            logger.info(f"[WEBSOCKET] Subscribed to {len(channels)} channels")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Subscription failed: {e}")
            return False
    
    async def listen(self):
        """Listen for messages"""
        self.running = True
        
        while self.running:
            try:
                if not self.websocket:
                    if not await self.connect():
                        await asyncio.sleep(self.reconnect_delay)
                        continue
                
                message = await asyncio.wait_for(
                    self.websocket.recv(),
                    timeout=30.0
                )
                
                self.last_message_time = time.time()
                data = json.loads(message)
                
                # Process message
                if self.callback:
                    await self.callback(data)
                    
            except asyncio.TimeoutError:
                # No message received, check connection
                if time.time() - self.last_message_time > 60:
                    logger.warning("[WARN] No messages for 60s, reconnecting...")
                    await self.reconnect()
            except websockets.exceptions.ConnectionClosed:
                logger.warning("[WARN] WebSocket connection closed, reconnecting...")
                await self.reconnect()
            except Exception as e:
                logger.error(f"[ERROR] Error in listen loop: {e}")
                await asyncio.sleep(1.0)
    
    async def reconnect(self):
        """Reconnect to WebSocket"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error(f"[ERROR] Max reconnect attempts ({self.max_reconnect_attempts}) reached")
            self.running = False
            return
        
        self.reconnect_attempts += 1
        logger.info(f"[WEBSOCKET] Reconnecting (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})...")
        
        try:
            if self.websocket:
                await self.websocket.close()
        except:
            pass
        
        await asyncio.sleep(self.reconnect_delay)
        await self.connect()
    
    async def close(self):
        """Close WebSocket connection"""
        self.running = False
        if self.websocket:
            try:
                await self.websocket.close()
                logger.info("[WEBSOCKET] Connection closed")
            except:
                pass


class MarketDataStream:
    """Market data stream manager"""
    
    def __init__(self, exchange: str, symbols: List[str], url: Optional[str] = None):
        self.exchange = exchange.lower()
        self.symbols = symbols
        
        # Build WebSocket URL
        if url:
            self.url = url
        elif self.exchange == "bybit":
            self.url = "wss://stream-testnet.bybit.com/v5/public/spot"
        elif self.exchange == "binance":
            self.url = "wss://testnet.binance.vision/stream"
        else:
            raise ValueError(f"Unsupported exchange: {exchange}")
        
        self.websocket_client = None
        self.ohlcv_data = {}  # {symbol: [candles]}
        self.orderbook_data = {}  # {symbol: {bids: [], asks: []}}
        self.callbacks = []
        
    async def start(self):
        """Start market data stream"""
        # Build channels
        channels = []
        
        if self.exchange == "bybit":
            # Bybit channels
            for symbol in self.symbols:
                channels.append(f"kline.5.{symbol}")
                channels.append(f"orderbook.20.{symbol}")
        else:
            # Binance channels
            streams = []
            for symbol in self.symbols:
                symbol_lower = symbol.lower()
                streams.append(f"{symbol_lower}@kline_5m")
                streams.append(f"{symbol_lower}@depth20@100ms")
            channels = streams
        
        # Create WebSocket client
        self.websocket_client = WebSocketClient(
            url=self.url,
            symbols=self.symbols,
            callback=self._handle_message
        )
        
        await self.websocket_client.connect()
        await self.websocket_client.subscribe(channels)
        
        # Start listening in background
        asyncio.create_task(self.websocket_client.listen())
        
        logger.info(f"[DATA] Market data stream started for {len(self.symbols)} symbols")
    
    async def _handle_message(self, message: Dict[str, Any]):
        """Handle incoming WebSocket message"""
        try:
            if self.exchange == "bybit":
                topic = message.get('topic', '')
                
                if 'kline' in topic:
                    # Kline data
                    data = message.get('data', [])
                    if isinstance(data, list):
                        for candle in data:
                            symbol = candle.get('symbol')
                            if symbol:
                                self._update_ohlcv(symbol, candle)
                    elif isinstance(data, dict):
                        # Single candle
                        symbol = data.get('symbol')
                        if symbol:
                            self._update_ohlcv(symbol, data)
                
                elif 'orderbook' in topic:
                    # Orderbook data
                    data = message.get('data', {})
                    symbol = data.get('s')
                    if symbol:
                        self.orderbook_data[symbol] = {
                            'bids': data.get('b', []),
                            'asks': data.get('a', []),
                            'timestamp': time.time()
                        }
            
            else:
                # Binance format
                stream = message.get('stream', '')
                data = message.get('data', {})
                
                if 'kline' in stream:
                    kline = data.get('k', {})
                    symbol = kline.get('s')
                    if symbol:
                        self._update_ohlcv(symbol, kline)
                
                elif 'depth' in stream:
                    symbol = data.get('s')
                    if symbol:
                        self.orderbook_data[symbol] = {
                            'bids': data.get('bids', []),
                            'asks': data.get('asks', []),
                            'timestamp': time.time()
                        }
            
            # Notify callbacks
            for callback in self.callbacks:
                try:
                    await callback(message)
                except Exception as e:
                    logger.error(f"[ERROR] Callback error: {e}")
                    
        except Exception as e:
            logger.error(f"[ERROR] Error handling message: {e}")
    
    def _update_ohlcv(self, symbol: str, candle_data: Dict[str, Any]):
        """Update OHLCV data"""
        if symbol not in self.ohlcv_data:
            self.ohlcv_data[symbol] = []
        
        # Convert to standard format
        if self.exchange == "bybit":
            candle = {
                'timestamp': int(candle_data.get('start', 0)),
                'open': float(candle_data.get('open', 0)),
                'high': float(candle_data.get('high', 0)),
                'low': float(candle_data.get('low', 0)),
                'close': float(candle_data.get('close', 0)),
                'volume': float(candle_data.get('volume', 0))
            }
        else:
            # Binance
            candle = {
                'timestamp': int(candle_data.get('t', 0)),
                'open': float(candle_data.get('o', 0)),
                'high': float(candle_data.get('h', 0)),
                'low': float(candle_data.get('l', 0)),
                'close': float(candle_data.get('c', 0)),
                'volume': float(candle_data.get('v', 0))
            }
        
        # Add or update
        candles = self.ohlcv_data[symbol]
        if candles and candles[-1]['timestamp'] == candle['timestamp']:
            # Update existing
            candles[-1] = candle
        else:
            # Add new
            candles.append(candle)
            # Keep only last 200 candles
            if len(candles) > 200:
                candles.pop(0)
    
    def get_latest_ohlcv(self, symbol: str, limit: int = 200) -> List[Dict[str, Any]]:
        """Get latest OHLCV data"""
        return self.ohlcv_data.get(symbol, [])[-limit:]
    
    def get_orderbook(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current orderbook"""
        return self.orderbook_data.get(symbol)
    
    def add_callback(self, callback: Callable):
        """Add callback for data updates"""
        self.callbacks.append(callback)
    
    async def stop(self):
        """Stop market data stream"""
        if self.websocket_client:
            await self.websocket_client.close()

