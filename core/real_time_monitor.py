"""
Real-time price monitoring for immediate profit taking
"""
import time
from threading import Thread, Event
from queue import Queue
from typing import Dict, Optional
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger("real_time_monitor")


class RealTimePriceMonitor:
    """Monitor prices in real-time for immediate profit taking"""
    
    def __init__(self, api_client, check_interval: float = 1.0):
        """
        Args:
            api_client: Binance API client
            check_interval: How often to check (seconds) - 1.0 = every second
        """
        self.api_client = api_client
        self.check_interval = check_interval
        self.running = False
        self.monitored_positions: Dict[str, Dict] = {}  # {symbol+strategy: {entry_price, target_price, ...}}
        self.price_updates = Queue()
        self.stop_event = Event()
        self.monitor_thread = None
    
    def add_position(
        self,
        symbol: str,
        strategy: str,
        entry_price: float,
        target_profit_pct: float,
        stop_loss_pct: float,
        action: str  # 'BUY' or 'SELL'
    ):
        """Add position to monitor"""
        try:
            key = f"{symbol}_{strategy}"
            
            if action.upper() == 'BUY':
                target_price = entry_price * (1 + target_profit_pct / 100.0)
                stop_price = entry_price * (1 - stop_loss_pct / 100.0)
            else:  # SELL (short)
                target_price = entry_price * (1 - target_profit_pct / 100.0)
                stop_price = entry_price * (1 + stop_loss_pct / 100.0)
            
            self.monitored_positions[key] = {
                'symbol': symbol,
                'strategy': strategy,
                'entry_price': entry_price,
                'target_price': target_price,
                'stop_price': stop_price,
                'target_profit_pct': target_profit_pct,
                'stop_loss_pct': stop_loss_pct,
                'action': action,
                'added_time': time.time()
            }
            
            logger.debug(f"[MONITOR] Added {key} - Target: ${target_price:.2f}, Stop: ${stop_price:.2f}")
            
        except Exception as e:
            logger.error(f"[ERROR] Error adding position to monitor: {e}")
    
    def remove_position(self, symbol: str, strategy: str):
        """Remove position from monitoring"""
        try:
            key = f"{symbol}_{strategy}"
            if key in self.monitored_positions:
                del self.monitored_positions[key]
                logger.debug(f"[MONITOR] Removed {key}")
        except Exception as e:
            logger.error(f"[ERROR] Error removing position: {e}")
    
    def start_monitoring(self):
        """Start real-time price monitoring"""
        if self.running:
            return
        
        self.running = True
        self.stop_event.clear()
        self.monitor_thread = Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info(f"[MONITOR] Real-time monitoring started (interval: {self.check_interval}s)")
    
    def _monitor_loop(self):
        """Continuous monitoring loop"""
        while self.running and not self.stop_event.is_set():
            try:
                # Check all monitored positions
                for key, position_info in list(self.monitored_positions.items()):
                    symbol = position_info['symbol']
                    current_price = self.api_client.get_current_price(symbol)
                    
                    if not current_price:
                        continue
                    
                    # Check if target or stop reached
                    target_reached = False
                    stop_hit = False
                    
                    if position_info['action'] == 'BUY':
                        if current_price >= position_info['target_price']:
                            target_reached = True
                        elif current_price <= position_info['stop_price']:
                            stop_hit = True
                    else:  # SELL (short)
                        if current_price <= position_info['target_price']:
                            target_reached = True
                        elif current_price >= position_info['stop_price']:
                            stop_hit = True
                    
                    # Send signal if target/stop reached
                    if target_reached:
                        self.price_updates.put({
                            'key': key,
                            'symbol': symbol,
                            'strategy': position_info['strategy'],
                            'signal': 'TAKE_PROFIT',
                            'current_price': current_price,
                            'position_info': position_info
                        })
                    elif stop_hit:
                        self.price_updates.put({
                            'key': key,
                            'symbol': symbol,
                            'strategy': position_info['strategy'],
                            'signal': 'STOP_LOSS',
                            'current_price': current_price,
                            'position_info': position_info
                        })
                
                # Wait before next check
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"[ERROR] Error in price monitoring: {e}")
                time.sleep(self.check_interval)
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.running = False
        self.stop_event.set()
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
        logger.info("[MONITOR] Real-time monitoring stopped")

