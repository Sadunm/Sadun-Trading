"""
Bybit API client with retry and error handling
Lower fees: 0.055% maker, 0.075% taker (vs Binance 0.1%)
"""
import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode
from typing import Optional, Dict, Any
from utils.errors import APIError
from utils.validators import validate_price
from utils.logger import setup_logger

logger = setup_logger("bybit_client")


class BybitClient:
    """Bybit API client with retry and error handling"""
    
    def __init__(self, api_key: str, secret_key: str, testnet: bool = True, max_retries: int = 3):
        self.api_key = api_key
        self.secret_key = secret_key
        self.testnet = testnet
        self.max_retries = max_retries
        
        # Set base URL (Bybit uses different endpoints for testnet)
        if testnet:
            self.base_url = "https://api-testnet.bybit.com"
        else:
            self.base_url = "https://api.bybit.com"
        
        # Symbol info cache
        self.symbol_info_cache: Dict[str, Dict] = {}
        
        logger.info(f"[OK] Bybit API Client initialized (testnet={testnet})")
    
    def _create_signature(self, params: Dict[str, Any]) -> str:
        """Create HMAC SHA256 signature for Bybit"""
        try:
            # Bybit signature format: sort params and create signature
            sorted_params = sorted(params.items())
            query_string = urlencode(sorted_params)
            signature = hmac.new(
                self.secret_key.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            return signature
        except Exception as e:
            raise APIError(f"Failed to create signature: {e}") from e
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
        timeout: int = 10
    ) -> requests.Response:
        """Make HTTP request with retry logic"""
        if params is None:
            params = {}
        
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                # Add signature if needed (Bybit format)
                if signed:
                    params['api_key'] = self.api_key
                    params['timestamp'] = int(time.time() * 1000)
                    params['recv_window'] = 5000
                    params['sign'] = self._create_signature(params)
                
                # Bybit uses different headers
                headers = {}
                if signed:
                    headers['Content-Type'] = 'application/json'
                
                # Make request
                if method.upper() == 'GET':
                    response = requests.get(url, params=params, headers=headers, timeout=timeout)
                elif method.upper() == 'POST':
                    response = requests.post(url, json=params, headers=headers, timeout=timeout)
                elif method.upper() == 'DELETE':
                    response = requests.delete(url, params=params, headers=headers, timeout=timeout)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                return response
                
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    raise APIError(f"Request timeout after {self.max_retries} attempts")
                wait_time = 2 ** attempt
                time.sleep(wait_time)
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limit
                    if attempt == self.max_retries - 1:
                        raise APIError("Rate limit exceeded")
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                else:
                    error_msg = f"HTTP {e.response.status_code}"
                    try:
                        error_data = e.response.json()
                        error_msg = error_data.get('ret_msg', error_msg)
                    except:
                        pass
                    raise APIError(error_msg) from e
                    
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise APIError(f"Request failed: {e}") from e
                wait_time = 2 ** attempt
                time.sleep(wait_time)
        
        raise APIError("Max retries exceeded")
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol"""
        try:
            # Bybit endpoint: /v5/market/tickers
            response = self._make_request(
                method='GET',
                endpoint='/v5/market/tickers',
                params={'category': 'spot', 'symbol': symbol.replace('USDT', 'USDT')}
            )
            
            data = response.json()
            if data.get('retCode') == 0:
                result = data.get('result', {})
                list_data = result.get('list', [])
                if list_data:
                    last_price = list_data[0].get('lastPrice')
                    if last_price:
                        return float(last_price)
            
            logger.warning(f"[WARN] Could not get price for {symbol}")
            return None
            
        except Exception as e:
            logger.error(f"[ERROR] Error getting price for {symbol}: {e}")
            return None
    
    def get_klines(
        self,
        symbol: str,
        interval: str = "5",
        limit: int = 200
    ) -> Optional[tuple]:
        """
        Get klines (candlestick data)
        Returns: (closes, highs, lows, volumes, opens) or None
        """
        try:
            # Bybit interval mapping (5m = "5", 1h = "60", etc.)
            interval_map = {
                "1m": "1", "3m": "3", "5m": "5", "15m": "15",
                "30m": "30", "1h": "60", "2h": "120", "4h": "240",
                "6h": "360", "12h": "720", "1d": "D", "1w": "W"
            }
            bybit_interval = interval_map.get(interval, interval.replace('m', '').replace('h', ''))
            
            response = self._make_request(
                method='GET',
                endpoint='/v5/market/kline',
                params={
                    'category': 'spot',
                    'symbol': symbol.replace('USDT', 'USDT'),
                    'interval': bybit_interval,
                    'limit': limit
                }
            )
            
            data = response.json()
            if data.get('retCode') == 0:
                result = data.get('result', {})
                klines = result.get('list', [])
                
                if not klines:
                    return None
                
                # Bybit format: [startTime, open, high, low, close, volume, turnover]
                # Reverse to get chronological order (oldest first)
                klines.reverse()
                
                closes = []
                highs = []
                lows = []
                volumes = []
                opens = []
                
                for kline in klines:
                    opens.append(float(kline[1]))   # open
                    highs.append(float(kline[2]))  # high
                    lows.append(float(kline[3]))   # low
                    closes.append(float(kline[4])) # close
                    volumes.append(float(kline[5])) # volume
                
                return (closes, highs, lows, volumes, opens)
            
            return None
            
        except Exception as e:
            logger.error(f"[ERROR] Error getting klines for {symbol}: {e}")
            return None
    
    def place_order(
        self,
        symbol: str,
        side: str,  # 'BUY' or 'SELL'
        quantity: float,
        price: Optional[float] = None,
        order_type: str = 'Market'  # 'Market' or 'Limit' (Bybit uses capital)
    ) -> Optional[Dict[str, Any]]:
        """
        Place an order on Bybit (for LIVE TRADING)
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            price: Limit price (required for LIMIT orders)
            order_type: 'Market' or 'Limit'
        
        Returns:
            Order response dict or None if failed
        """
        try:
            from utils.validators import validate_price
            
            # Validate inputs
            if not validate_price(quantity) or quantity <= 0:
                logger.error(f"[ERROR] Invalid quantity: {quantity}")
                return None
            
            if order_type == 'Limit' and (not price or not validate_price(price)):
                logger.error(f"[ERROR] LIMIT order requires valid price: {price}")
                return None
            
            # Prepare parameters
            params = {
                'category': 'spot',
                'symbol': symbol.replace('USDT', 'USDT').upper(),
                'side': 'Buy' if side.upper() == 'BUY' else 'Sell',
                'orderType': order_type,
                'qty': str(quantity),  # Bybit requires string
            }
            
            # Add price for LIMIT orders
            if order_type == 'Limit':
                params['price'] = str(price)
                params['timeInForce'] = 'GTC'  # Good Till Cancel
            
            # Make signed request
            response = self._make_request(
                method='POST',
                endpoint='/v5/order/create',
                params=params,
                signed=True
            )
            
            order_data = response.json()
            
            # Check response
            if order_data.get('retCode') != 0:
                error_msg = order_data.get('retMsg', 'Unknown error')
                logger.error(f"[ERROR] Bybit order failed: {error_msg}")
                return None
            
            result = order_data.get('result', {})
            
            # For market orders, extract fill price
            if order_type == 'Market' and 'fills' in result:
                fills = result.get('fills', [])
                if fills:
                    total_qty = 0.0
                    total_cost = 0.0
                    for fill in fills:
                        fill_qty = float(fill.get('execQty', 0))
                        fill_price = float(fill.get('execPrice', 0))
                        total_qty += fill_qty
                        total_cost += fill_qty * fill_price
                    
                    if total_qty > 0:
                        avg_price = total_cost / total_qty
                        result['avg_fill_price'] = avg_price
                        logger.info(f"[OK] Market order filled: {side} {quantity} {symbol} @ avg ${avg_price:.2f}")
            
            logger.info(f"[OK] Bybit order placed: {side} {quantity} {symbol} @ {order_type}")
            return result
            
        except Exception as e:
            logger.error(f"[ERROR] Order placement failed: {e}", exc_info=True)
            return None
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get account information"""
        try:
            response = self._make_request(
                method='GET',
                endpoint='/v5/account/wallet-balance',
                params={'accountType': 'SPOT'},
                signed=True
            )
            
            data = response.json()
            if data.get('retCode') == 0:
                return data.get('result', {})
            
            return None
            
        except Exception as e:
            logger.error(f"[ERROR] Error getting account info: {e}")
            return None


