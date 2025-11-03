"""
Real-time price monitoring for immediate profit taking
"""
import time
from threading import Thread, Event, Lock
from queue import Queue
from typing import Dict, Optional
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger("real_time_monitor")


class RealTimePriceMonitor:
    """Monitor prices in real-time for immediate profit taking"""
    
    def __init__(self, api_client, fee_calculator=None, slippage_simulator=None, spread_simulator=None, check_interval: float = 1.0):
        """
        Args:
            api_client: Binance API client
            fee_calculator: Fee calculator for cost calculation
            slippage_simulator: Slippage simulator
            spread_simulator: Spread simulator
            check_interval: How often to check (seconds) - 1.0 = every second
        """
        self.api_client = api_client
        self.fee_calculator = fee_calculator
        self.slippage_simulator = slippage_simulator
        self.spread_simulator = spread_simulator
        self.check_interval = check_interval
        self.running = False
        self.monitored_positions: Dict[str, Dict] = {}  # {symbol+strategy: {entry_price, target_price, quantity, ...}}
        self.positions_lock = Lock()  # Thread safety for monitored_positions
        self.price_updates = Queue()
        self.stop_event = Event()
        self.monitor_thread = None
    
    def add_position(
        self,
        symbol: str,
        strategy: str,
        entry_price: float,
        quantity: float,
        target_profit_pct: float,
        stop_loss_pct: float,
        action: str,  # 'BUY' or 'SELL'
        partial_profit_enabled: bool = False  # Enable partial profit taking
    ):
        """Add position to monitor (thread-safe)"""
        try:
            key = f"{symbol}_{strategy}"
            
            # Calculate prices with buffer for stop loss (to account for exit slippage/spread)
            # Buffer: ~0.15% for spread + slippage on exit (INCREASED to account for REAL exit costs seen in losses)
            # Actual losses (0.50-0.59%) show we need more room beyond stop loss price
            stop_loss_buffer_pct = 0.15
            effective_sl_pct = stop_loss_pct + stop_loss_buffer_pct
            
            if action.upper() == 'BUY':
                target_price = entry_price * (1 + target_profit_pct / 100.0)
                stop_price = entry_price * (1 - effective_sl_pct / 100.0)  # Buffer added
            else:  # SELL (short)
                target_price = entry_price * (1 - target_profit_pct / 100.0)
                stop_price = entry_price * (1 + effective_sl_pct / 100.0)  # Buffer added
            
            # Calculate breakeven + small profit price (fees covered + 0.05% profit)
            breakeven_price = self._calculate_breakeven_plus_profit(
                symbol, entry_price, quantity, action, min_profit_pct=0.05
            )
            
            with self.positions_lock:
                self.monitored_positions[key] = {
                    'symbol': symbol,
                    'strategy': strategy,
                    'entry_price': entry_price,
                    'quantity': quantity,
                    'target_price': target_price,
                    'stop_price': stop_price,
                    'breakeven_profit_price': breakeven_price,  # Price where fees covered + small profit
                    'target_profit_pct': target_profit_pct,
                    'stop_loss_pct': stop_loss_pct,
                    'action': action,
                    'partial_profit_enabled': partial_profit_enabled,  # Your smart idea!
                    'added_time': time.time()
                }
            
            logger.debug(f"[MONITOR] Added {key} - Target: ${target_price:.2f}, Breakeven+Profit: ${breakeven_price:.2f}, Stop: ${stop_price:.2f}")
            
        except Exception as e:
            logger.error(f"[ERROR] Error adding position to monitor: {e}")
    
    def _calculate_breakeven_plus_profit(
        self,
        symbol: str,
        entry_price: float,
        quantity: float,
        action: str,
        min_profit_pct: float = 0.05  # 0.05% minimum profit after fees
    ) -> float:
        """
        Calculate price where fees are covered + minimum profit achieved
        Returns the exit price needed to break even + small profit
        """
        try:
            if not self.fee_calculator:
                # Fallback: simple calculation
                if action == 'BUY':
                    return entry_price * (1 + 0.0025)  # Assume 0.25% total costs
                else:
                    return entry_price * (1 - 0.0025)
            
            # Position value
            position_value = entry_price * quantity
            
            # Calculate total fees (entry + exit)
            round_trip_fee = self.fee_calculator.calculate_round_trip_fee(position_value)
            fee_pct = (round_trip_fee / position_value) if position_value > 0 else 0.002  # 0.2% default
            
            # Estimate slippage + spread (average)
            slippage_pct = 0.0003  # 0.03%
            spread_pct = 0.0005 if self.spread_simulator else 0.0005  # 0.05%
            
            # Total costs percentage
            total_costs_pct = fee_pct + slippage_pct + spread_pct
            
            # Add minimum profit
            target_pct = total_costs_pct + (min_profit_pct / 100.0)
            
            # Calculate exit price
            if action == 'BUY':
                # Need to sell at higher price to cover costs + profit
                breakeven_price = entry_price * (1 + target_pct)
            else:  # SELL (short)
                # Need to buy at lower price to cover costs + profit
                breakeven_price = entry_price * (1 - target_pct)
            
            return breakeven_price
            
        except Exception as e:
            logger.error(f"[ERROR] Error calculating breakeven price: {e}")
            # Fallback
            if action == 'BUY':
                return entry_price * 1.003  # 0.3% above entry
            else:
                return entry_price * 0.997  # 0.3% below entry
    
    def remove_position(self, symbol: str, strategy: str):
        """Remove position from monitoring (thread-safe)"""
        try:
            key = f"{symbol}_{strategy}"
            with self.positions_lock:
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
        check_count = 0
        while self.running and not self.stop_event.is_set():
            try:
                check_count += 1
                
                # Get snapshot of positions (thread-safe)
                with self.positions_lock:
                    monitored_count = len(self.monitored_positions)
                    positions_snapshot = list(self.monitored_positions.items())
                
                # Log status every 60 checks (every ~60 seconds at 1s interval)
                if check_count % 60 == 0:
                    logger.debug(f"[MONITOR] Monitoring {monitored_count} positions (check #{check_count})")
                
                if monitored_count == 0:
                    time.sleep(self.check_interval)
                    continue
                
                # Check all monitored positions (using snapshot to avoid lock during price checks)
                for key, position_info in positions_snapshot:
                    try:
                        # SAFE: Get all required values with defaults
                        symbol = position_info.get('symbol')
                        if not symbol:
                            continue  # Skip if no symbol
                        
                        strategy = position_info.get('strategy', 'unknown')
                        
                        # Safe strategy string for f-string (handle any edge cases)
                        try:
                            strategy_str = str(strategy) if strategy else 'unknown'
                            strategy_safe = strategy_str.replace('{', '{{').replace('}', '}}')
                        except Exception:
                            strategy_safe = 'unknown'  # Fallback if any error
                        
                        # Get price (round-robin if available, otherwise direct)
                        if hasattr(self.api_client, 'get_client'):
                            # API rotator
                            client = self.api_client.get_client()
                            current_price = client.get_current_price(symbol)
                        else:
                            # Direct client
                            current_price = self.api_client.get_current_price(symbol)
                        
                        if not current_price:
                            if check_count % 60 == 0:  # Log occasionally to avoid spam
                                logger.warning(f"[MONITOR] Could not get price for {symbol}")
                            continue
                        
                        # Check if target, breakeven+profit, or stop reached
                        target_reached = False
                        breakeven_profit_reached = False
                        stop_hit = False
                        
                        breakeven_price = position_info.get('breakeven_profit_price', None)
                        entry_price = position_info.get('entry_price')
                        target_price = position_info.get('target_price')
                        stop_price = position_info.get('stop_price')
                        action = position_info.get('action', 'BUY')
                        
                        # Validate all required values
                        if entry_price is None or target_price is None or stop_price is None:
                            logger.warning(f"[MONITOR] Missing price data for {symbol}, skipping")
                            continue
                    
                        if action == 'BUY':
                            if current_price >= target_price:
                                target_reached = True
                            elif breakeven_price and current_price >= breakeven_price:
                                breakeven_profit_reached = True
                            elif current_price <= stop_price:
                                stop_hit = True
                        else:  # SELL (short)
                            if current_price <= target_price:
                                target_reached = True
                            elif breakeven_price and current_price <= breakeven_price:
                                breakeven_profit_reached = True
                            elif current_price >= stop_price:
                                stop_hit = True
                        
                        # Log detailed status every 60 checks for debugging
                        if check_count % 60 == 0:
                            pct_change = ((current_price - entry_price) / entry_price * 100.0) if entry_price > 0 else 0.0
                            logger.debug(
                                f"[MONITOR] {symbol} ({strategy_safe}): "
                                f"Price=${current_price:.2f} (Entry=${entry_price:.2f}, {pct_change:+.2f}%), "
                                f"Target=${target_price:.2f}, "
                                f"Breakeven+Profit=${breakeven_price:.2f if breakeven_price else 'N/A'}, "
                                f"Stop=${stop_price:.2f}"
                            )
                        
                        # Priority: Target > Breakeven+Profit (Partial) > Stop Loss
                        # Send signal if any condition reached (check every iteration, not just every 60)
                        if target_reached:
                            logger.info(f"[MONITOR] {symbol} ({strategy_safe}) TARGET REACHED! Price: ${current_price:.2f}")
                            self.price_updates.put({
                                'key': key,
                                'symbol': symbol,
                                'strategy': position_info.get('strategy', 'unknown'),
                                'signal': 'TAKE_PROFIT',
                                'current_price': current_price,
                                'position_info': position_info
                            })
                        elif breakeven_profit_reached:
                            # Fees covered + small profit achieved
                            # Check if partial profit taking enabled
                            if position_info.get('partial_profit_enabled', False):
                                # PARTIAL CLOSE: Close fees amount, keep rest for target
                                logger.info(f"[MONITOR] {symbol} ({strategy_safe}) FEES COVERED! Partial close at ${current_price:.2f} (Breakeven: ${breakeven_price:.2f})")
                                self.price_updates.put({
                                    'key': key,
                                    'symbol': symbol,
                                    'strategy': position_info.get('strategy', 'unknown'),
                                    'signal': 'PARTIAL_FEES_PROFIT',
                                    'current_price': current_price,
                                    'position_info': position_info
                                })
                            else:
                                # FULL CLOSE: Old behavior (close everything)
                                logger.info(f"[MONITOR] {symbol} ({strategy_safe}) BREAKEVEN+PROFIT REACHED! Full close at ${current_price:.2f}")
                                self.price_updates.put({
                                    'key': key,
                                    'symbol': symbol,
                                    'strategy': position_info.get('strategy', 'unknown'),
                                    'signal': 'BREAKEVEN_PROFIT',
                                    'current_price': current_price,
                                    'position_info': position_info
                                })
                        elif stop_hit:
                            logger.warning(f"[MONITOR] {symbol} ({strategy_safe}) STOP LOSS HIT! Price: ${current_price:.2f}")
                            self.price_updates.put({
                                'key': key,
                                'symbol': symbol,
                                'strategy': position_info.get('strategy', 'unknown'),
                                'signal': 'STOP_LOSS',
                                'current_price': current_price,
                                'position_info': position_info
                            })
                    except Exception as e:
                        # Handle per-position errors gracefully
                        logger.error(f"[ERROR] Error monitoring position {key}: {e}", exc_info=True)
                        continue  # Skip this position, continue with others
                
                # Wait before next check
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"[ERROR] Error in price monitoring loop: {e}", exc_info=True)
                time.sleep(self.check_interval)
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.running = False
        self.stop_event.set()
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
        logger.info("[MONITOR] Real-time monitoring stopped")

