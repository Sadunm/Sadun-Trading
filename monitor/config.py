"""
Configuration for isolated monitoring system
"""
import os
from typing import Dict, Any

class MonitorConfig:
    """Configuration for monitoring system"""
    
    def __init__(self):
        # Bot API connection
        self.bot_api_url = os.getenv('BOT_API_URL', 'http://localhost:10000')
        self.bot_api_timeout = 5.0  # seconds
        
        # Refresh intervals
        self.stats_refresh_interval = 2.0  # seconds
        self.trades_refresh_interval = 3.0  # seconds
        self.signals_refresh_interval = 1.0  # seconds
        
        # Data storage
        self.log_file = 'monitor/logs/monitor.log'
        self.data_dir = 'monitor/data'
        
        # Analysis settings
        self.chart_history_days = 7  # days of history for charts
        self.performance_window_hours = 24  # hours for performance analysis
        
    def get_config(self) -> Dict[str, Any]:
        """Get all config as dict"""
        return {
            'bot_api_url': self.bot_api_url,
            'refresh_intervals': {
                'stats': self.stats_refresh_interval,
                'trades': self.trades_refresh_interval,
                'signals': self.signals_refresh_interval
            },
            'data_storage': {
                'log_file': self.log_file,
                'data_dir': self.data_dir
            },
            'analysis': {
                'chart_history_days': self.chart_history_days,
                'performance_window_hours': self.performance_window_hours
            }
        }

