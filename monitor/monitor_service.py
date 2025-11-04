"""
Monitoring Service - Main service that connects to bot and analyzes
"""
import time
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from monitor.bot_connector import BotConnector
from monitor.analyzer import TradeAnalyzer
from monitor.config import MonitorConfig
from utils.logger import setup_logger

logger = setup_logger("monitor_service")


class MonitorService:
    """Main monitoring service - completely isolated from bot"""
    
    def __init__(self, config: Optional[MonitorConfig] = None):
        self.config = config or MonitorConfig()
        self.connector = BotConnector(
            api_url=self.config.bot_api_url,
            timeout=self.config.bot_api_timeout
        )
        self.analyzer = TradeAnalyzer()
        self.running = False
        self.data_history = []
        
        # Create data directory
        Path(self.config.data_dir).mkdir(parents=True, exist_ok=True)
        Path('monitor/logs').mkdir(parents=True, exist_ok=True)
    
    def start(self):
        """Start monitoring service"""
        logger.info("[START] Monitoring Service Starting...")
        logger.info(f"[CONFIG] Bot API URL: {self.config.bot_api_url}")
        
        # Check connection
        if not self.connector.check_connection():
            logger.error(f"[ERROR] Cannot connect to bot at {self.config.bot_api_url}")
            logger.error(f"[ERROR] {self.connector.last_error}")
            logger.error("[ERROR] Make sure bot is running and API server is accessible")
            return False
        
        logger.info("[OK] Connected to bot API")
        self.running = True
        
        # Start monitoring loop
        try:
            self._monitoring_loop()
        except KeyboardInterrupt:
            logger.info("[STOP] Monitoring service stopped by user")
            self.running = False
        except Exception as e:
            logger.error(f"[ERROR] Monitoring loop error: {e}", exc_info=True)
            self.running = False
        
        return True
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("[MONITOR] Starting monitoring loop...")
        
        last_stats_refresh = 0
        last_trades_refresh = 0
        
        while self.running:
            try:
                current_time = time.time()
                
                # Refresh stats
                if current_time - last_stats_refresh >= self.config.stats_refresh_interval:
                    self._refresh_stats()
                    last_stats_refresh = current_time
                
                # Refresh trades
                if current_time - last_trades_refresh >= self.config.trades_refresh_interval:
                    self._refresh_trades()
                    last_trades_refresh = current_time
                
                # Small sleep to prevent CPU spinning
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"[ERROR] Error in monitoring loop: {e}", exc_info=True)
                time.sleep(1.0)
    
    def _refresh_stats(self):
        """Refresh bot statistics"""
        try:
            stats = self.connector.get_stats()
            if stats:
                logger.debug(f"[STATS] Capital: ${stats.get('current_capital', 0):.2f}, "
                           f"P&L: ${stats.get('total_pnl', 0):.2f}, "
                           f"Trades: {stats.get('total_trades', 0)}")
        except Exception as e:
            logger.error(f"[ERROR] Error refreshing stats: {e}")
    
    def _refresh_trades(self):
        """Refresh and analyze trades"""
        try:
            trades = self.connector.get_trades()
            if trades:
                analysis = self.analyzer.analyze_trades(trades)
                patterns = self.analyzer.detect_patterns(trades)
                
                # Save analysis
                self._save_analysis(analysis, patterns)
                
                logger.info(f"[ANALYSIS] Trades: {analysis.get('total_trades', 0)}, "
                          f"Win Rate: {analysis.get('win_rate', 0):.1f}%, "
                          f"Net Profit: ${analysis.get('net_profit', 0):.2f}")
        except Exception as e:
            logger.error(f"[ERROR] Error refreshing trades: {e}")
    
    def _save_analysis(self, analysis: Dict[str, Any], patterns: Dict[str, Any]):
        """Save analysis to file"""
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'analysis': analysis,
                'patterns': patterns
            }
            
            self.data_history.append(data)
            
            # Keep only last 1000 entries
            if len(self.data_history) > 1000:
                self.data_history = self.data_history[-1000:]
            
            # Save to file
            filename = f"{self.config.data_dir}/analysis_{datetime.now().strftime('%Y%m%d')}.json"
            with open(filename, 'w') as f:
                json.dump(self.data_history, f, indent=2)
                
        except Exception as e:
            logger.error(f"[ERROR] Error saving analysis: {e}")
    
    def get_current_analysis(self) -> Dict[str, Any]:
        """Get current analysis"""
        try:
            all_data = self.connector.get_all_data()
            trades = all_data.get('trades', [])
            
            analysis = self.analyzer.analyze_trades(trades)
            patterns = self.analyzer.detect_patterns(trades)
            
            return {
                'bot_data': all_data,
                'analysis': analysis,
                'patterns': patterns,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"[ERROR] Error getting current analysis: {e}")
            return {'error': str(e)}
    
    def stop(self):
        """Stop monitoring service"""
        logger.info("[STOP] Stopping monitoring service...")
        self.running = False

