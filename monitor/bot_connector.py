"""
Bot Connector - Connects to Trading Bot API (isolated)
"""
import requests
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
from utils.logger import setup_logger

logger = setup_logger("monitor_connector")


class BotConnector:
    """Connects to Trading Bot API - completely isolated"""
    
    def __init__(self, api_url: str = 'http://localhost:10000', timeout: float = 5.0):
        self.api_url = api_url.rstrip('/')
        self.timeout = timeout
        self.last_error = None
        self.connection_status = False
        
    def check_connection(self) -> bool:
        """Check if bot API is accessible"""
        try:
            response = requests.get(f"{self.api_url}/api/stats", timeout=self.timeout)
            if response.status_code == 200:
                self.connection_status = True
                self.last_error = None
                return True
            else:
                self.connection_status = False
                self.last_error = f"HTTP {response.status_code}"
                return False
        except requests.exceptions.ConnectionError:
            self.connection_status = False
            self.last_error = "Connection refused - Bot not running?"
            return False
        except requests.exceptions.Timeout:
            self.connection_status = False
            self.last_error = "Timeout - Bot not responding"
            return False
        except Exception as e:
            self.connection_status = False
            self.last_error = str(e)
            logger.error(f"[ERROR] Connection check failed: {e}")
            return False
    
    def get_stats(self) -> Optional[Dict[str, Any]]:
        """Get bot statistics"""
        try:
            response = requests.get(f"{self.api_url}/api/stats", timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"[WARN] Stats API returned {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"[ERROR] Error getting stats: {e}")
            return None
    
    def get_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get trade history"""
        try:
            response = requests.get(f"{self.api_url}/api/trades", timeout=self.timeout)
            if response.status_code == 200:
                trades = response.json()
                return trades[:limit] if isinstance(trades, list) else []
            else:
                logger.warning(f"[WARN] Trades API returned {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"[ERROR] Error getting trades: {e}")
            return []
    
    def get_performance_summary(self) -> Optional[Dict[str, Any]]:
        """Get performance summary"""
        try:
            response = requests.get(f"{self.api_url}/api/performance/summary", timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"[WARN] Performance API returned {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"[ERROR] Error getting performance: {e}")
            return None
    
    def get_daily_performance(self) -> Optional[Dict[str, Any]]:
        """Get daily performance"""
        try:
            response = requests.get(f"{self.api_url}/api/performance/daily", timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"[WARN] Daily performance API returned {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"[ERROR] Error getting daily performance: {e}")
            return None
    
    def get_strategy_performance(self) -> Optional[Dict[str, Any]]:
        """Get strategy performance breakdown"""
        try:
            response = requests.get(f"{self.api_url}/api/performance/strategy", timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"[WARN] Strategy performance API returned {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"[ERROR] Error getting strategy performance: {e}")
            return None
    
    def get_compounding_stats(self) -> Optional[Dict[str, Any]]:
        """Get compounding statistics"""
        try:
            response = requests.get(f"{self.api_url}/api/compounding", timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"[WARN] Compounding API returned {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"[ERROR] Error getting compounding stats: {e}")
            return None
    
    def get_all_data(self) -> Dict[str, Any]:
        """Get all available data from bot"""
        return {
            'stats': self.get_stats(),
            'trades': self.get_trades(),
            'performance': self.get_performance_summary(),
            'daily': self.get_daily_performance(),
            'strategy': self.get_strategy_performance(),
            'compounding': self.get_compounding_stats(),
            'timestamp': datetime.now().isoformat(),
            'connection_status': self.connection_status
        }

