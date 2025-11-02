"""
Round-robin API key rotation for distributing load across multiple keys
"""
import time
from threading import Lock
from typing import List, Tuple, Optional
from core.api_client import BinanceAPIClient
from utils.logger import setup_logger

logger = setup_logger("api_rotator")


class APIRotator:
    """
    Round-robin API key rotation
    Distributes load across multiple API keys to avoid rate limits
    """
    
    def __init__(self, api_keys: List[Tuple[str, str]], testnet: bool = True):
        """
        Initialize with list of (api_key, secret_key) tuples
        
        Args:
            api_keys: List of (api_key, secret_key) tuples
            testnet: Use testnet (True) or production (False)
        """
        if not api_keys:
            raise ValueError("At least one API key pair required")
        
        self.api_keys = api_keys
        self.testnet = testnet
        self.current_index = 0
        self.lock = Lock()
        
        # Initialize clients
        self.clients: List[BinanceAPIClient] = []
        for api_key, secret_key in api_keys:
            client = BinanceAPIClient(
                api_key=api_key,
                secret_key=secret_key,
                testnet=testnet,
                max_retries=3
            )
            self.clients.append(client)
        
        # Track weight usage per client
        self.weights = [0] * len(self.clients)
        self.last_reset = time.time()
        self.weight_limit = 1000  # Binance limit: 1000 weight per minute
        
        logger.info(f"[API-ROTATOR] Initialized with {len(self.clients)} API keys")
    
    def get_client(self) -> BinanceAPIClient:
        """Get next client in round-robin fashion"""
        with self.lock:
            # Reset weights every minute
            if time.time() - self.last_reset > 60:
                self.weights = [0] * len(self.clients)
                self.last_reset = time.time()
            
            # Find client with lowest weight
            min_weight = min(self.weights)
            client_index = self.weights.index(min_weight)
            
            # Rotate if weight limit approaching
            if min_weight >= self.weight_limit * 0.8:  # 80% threshold
                client_index = (self.current_index + 1) % len(self.clients)
                logger.warning(f"[API-ROTATOR] Weight limit approaching, rotating to key {client_index + 1}")
            
            self.current_index = client_index
            return self.clients[client_index]
    
    def add_weight(self, client_index: int, weight: int):
        """Add weight to client (tracking API usage)"""
        with self.lock:
            if 0 <= client_index < len(self.weights):
                self.weights[client_index] += weight
    
    def ping_test(self, max_latency_ms: int = 100) -> Tuple[bool, Optional[int]]:
        """
        Test API latency
        Returns: (success, latency_ms)
        """
        try:
            start_time = time.time()
            client = self.get_client()
            price = client.get_current_price('BTCUSDT')
            end_time = time.time()
            
            latency_ms = int((end_time - start_time) * 1000)
            
            if price and latency_ms <= max_latency_ms:
                return True, latency_ms
            else:
                logger.warning(f"[API-ROTATOR] High latency: {latency_ms}ms (limit: {max_latency_ms}ms)")
                return False, latency_ms
                
        except Exception as e:
            logger.error(f"[API-ROTATOR] Ping test failed: {e}")
            return False, None

