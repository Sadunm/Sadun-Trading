"""
Binance API client with retry and error handling
"""
import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode
from typing import Optional, Dict, Any, Tuple
from utils.errors import APIError
from utils.validators import validate_price
from utils.logger import setup_logger

logger = setup_logger("api_client")


class BinanceAPIClient:
    """Binance API client with retry and error handling"""
    
    def __init__(self, api_key: str, secret_key: str, testnet: bool = True, max_retries: int = 3):
        self.api_key = api_key
        self.secret_key = secret_key
        self.testnet = testnet
        self.max_retries = max_retries
        
        # Set base URL
        if testnet:
            self.base_url = "https://testnet.binance.vision"
        else:
            self.base_url = "https://api.binance.com"
        
        # Symbol info cache
        self.symbol_info_cache: Dict[str, Dict] = {}
        
        logger.info(f"[OK] Binance API Client initialized (testnet={testnet})")
    
    def _create_signature(self, params: Dict[str, Any]) -> str:
        """Create HMAC SHA256 signature"""
        try:
            query_string = urlencode(params)
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
                # Add signature if needed
                if signed:
                    params['timestamp'] = int(time.time() * 1000)
                    params['signature'] = self._create_signature(params)
                
                # Add API key to headers
                headers = {}
                if signed:
                    headers['X-MBX-APIKEY'] = self.api_key
                
                # Make request
                if method.upper() == 'GET':
                    response = requests.get(url, params=params, headers=headers, timeout=timeout)
                elif method.upper() == 'POST':
                    response = requests.post(url, data=params, headers=headers, timeout=timeout)
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
                    raise APIError(f"HTTP error: {e}") from e
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise APIError(f"Request failed: {e}") from e
                wait_time = 2 ** attempt
                time.sleep(wait_time)
        
        raise APIError("Max retries exceeded")
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol"""
        try:
            response = self._make_request('GET', '/api/v3/ticker/price', {'symbol': symbol})
            data = response.json()
            price = float(data['price'])
            
            if not validate_price(price):
                raise ValueError(f"Invalid price: {price}")
            
            return price
        except Exception as e:
            logger.error(f"[ERROR] Error getting price for {symbol}: {e}")
            return None
    
    def get_klines(self, symbol: str, interval: str = "5m", limit: int = 200) -> Optional[Tuple]:
        """Get kline/candlestick data"""
        try:
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            response = self._make_request('GET', '/api/v3/klines', params)
            klines = response.json()
            
            # Parse klines
            closes = [float(k[4]) for k in klines]
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]
            volumes = [float(k[5]) for k in klines]
            opens = [float(k[1]) for k in klines]
            
            return closes, highs, lows, volumes, opens
        except Exception as e:
            logger.error(f"[ERROR] Error getting klines for {symbol}: {e}")
            return None
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get account information"""
        try:
            response = self._make_request('GET', '/api/v3/account', {}, signed=True)
            return response.json()
        except Exception as e:
            logger.error(f"[ERROR] Error getting account info: {e}")
            return None
    
    def _format_quantity(self, symbol: str, quantity: float) -> str:
        """Format quantity according to Binance precision"""
        try:
            # Get symbol info (cached)
            if symbol not in self.symbol_info_cache:
                self._load_symbol_info(symbol)
            
            symbol_info = self.symbol_info_cache.get(symbol, {})
            lot_size = symbol_info.get('lot_size_filter', {})
            step_size = float(lot_size.get('stepSize', '0.001'))
            
            # Calculate precision
            precision = 0
            temp = step_size
            while temp < 1:
                temp *= 10
                precision += 1
            
            # Round to step size
            rounded = round(quantity / step_size) * step_size
            return f"{rounded:.{precision}f}".rstrip('0').rstrip('.')
            
        except Exception:
            # Fallback: use 8 decimals
            return f"{quantity:.8f}".rstrip('0').rstrip('.')
    
    def _format_price(self, symbol: str, price: float) -> str:
        """Format price according to Binance precision"""
        try:
            if symbol not in self.symbol_info_cache:
                self._load_symbol_info(symbol)
            
            symbol_info = self.symbol_info_cache.get(symbol, {})
            price_filter = symbol_info.get('price_filter', {})
            tick_size = float(price_filter.get('tickSize', '0.01'))
            
            # Calculate precision
            precision = 0
            temp = tick_size
            while temp < 1:
                temp *= 10
                precision += 1
            
            # Round to tick size
            rounded = round(price / tick_size) * tick_size
            return f"{rounded:.{precision}f}".rstrip('0').rstrip('.')
            
        except Exception:
            # Fallback: use 2 decimals
            return f"{price:.2f}"
    
    def _load_symbol_info(self, symbol: str):
        """Load symbol trading rules from Binance"""
        try:
            response = self._make_request(
                'GET',
                '/api/v3/exchangeInfo',
                params={'symbol': symbol.upper()}
            )
            
            data = response.json()
            for s in data.get('symbols', []):
                if s['symbol'] == symbol.upper():
                    filters = {f['filterType']: f for f in s.get('filters', [])}
                    self.symbol_info_cache[symbol] = {
                        'baseAssetPrecision': s.get('baseAssetPrecision', 8),
                        'quoteAssetPrecision': s.get('quoteAssetPrecision', 8),
                        'lot_size_filter': filters.get('LOT_SIZE', {}),
                        'price_filter': filters.get('PRICE_FILTER', {}),
                        'min_notional': filters.get('MIN_NOTIONAL', {}).get('minNotional', '0')
                    }
                    break
        except Exception as e:
            logger.warning(f"[WARN] Could not load symbol info for {symbol}: {e}")

