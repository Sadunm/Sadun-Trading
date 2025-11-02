"""
Main trading bot orchestrator - Live Matching Version
"""
import time
from threading import Lock, Thread
from queue import Empty
from datetime import datetime
from typing import Dict, Any, Optional
from core.api_client import BinanceAPIClient
from core.position_manager import PositionManager
from core.risk_manager import RiskManager
from core.state_manager import StateManager
from core.fee_calculator import FeeCalculator
from core.slippage_simulator import SlippageSimulator, SpreadSimulator
from core.compound_manager import CompoundManager
from core.real_time_monitor import RealTimePriceMonitor
from data.market_data import MarketData
from data.storage import TradeStorage
from indicators.calculator import IndicatorCalculator
from indicators.market_regime import MarketRegimeDetector
from strategies.scalping import ScalpingStrategy
from strategies.day_trading import DayTradingStrategy
from strategies.momentum import MomentumStrategy
from utils.config_loader import get_config
from utils.profit_calculator import ProfitCalculator
from utils.validators import clamp_value
from utils.logger import setup_logger

logger = setup_logger("bot")


class TradingBot:
    """Main trading bot orchestrator"""
    
    def __init__(self, api_key: str, secret_key: str):
        # Load config
        try:
            self.config = get_config()
        except Exception:
            from utils.config_loader import load_config
            load_config()
            self.config = get_config()
        
        trading_config = self.config.get_trading_config()
        risk_config = self.config.get_risk_config()
        
        # Trading type
        self.trading_type = trading_config.get('trading_type', 'spot')
        self.use_maker_orders = trading_config.get('use_maker_orders', False)
        
        # Initialize components
        self.api_client = BinanceAPIClient(
            api_key=api_key,
            secret_key=secret_key,
            testnet=trading_config.get('testnet', True),
            max_retries=self.config.get_api_config().get('max_retries', 3)
        )
        
        self.market_data = MarketData(
            api_client=self.api_client,
            cache_duration=self.config.get_api_config().get('cache_duration', 5)
        )
        
        # Fee and cost calculators
        self.fee_calculator = FeeCalculator(self.trading_type, self.use_maker_orders)
        self.slippage_simulator = SlippageSimulator()
        self.spread_simulator = SpreadSimulator()
        self.profit_calculator = ProfitCalculator(self.trading_type, self.use_maker_orders)
        
        self.position_manager = PositionManager()
        self.risk_manager = RiskManager(risk_config)
        self.state_manager = StateManager()
        self.trade_storage = TradeStorage()
        
        # Auto compounding
        self.compound_manager = CompoundManager(trading_config)
        
        # Real-time price monitor for immediate profit taking
        self.price_monitor = RealTimePriceMonitor(
            api_client=self.api_client,
            fee_calculator=self.fee_calculator,
            slippage_simulator=self.slippage_simulator,
            spread_simulator=self.spread_simulator,
            check_interval=trading_config.get('price_check_interval', 1.0)
        )
        self.price_monitor.start_monitoring()
        
        # Start price monitor handler
        self._start_price_monitor_handler()
        
        # Initialize strategies
        strategies_config = self.config.get_strategy_config()
        self.strategies = {}
        
        if strategies_config.get('scalping', {}).get('enabled', True):
            self.strategies['scalping'] = ScalpingStrategy('scalping', strategies_config.get('scalping', {}))
        
        if strategies_config.get('day_trading', {}).get('enabled', True):
            self.strategies['day_trading'] = DayTradingStrategy('day_trading', strategies_config.get('day_trading', {}))
        
        if strategies_config.get('momentum', {}).get('enabled', True):
            self.strategies['momentum'] = MomentumStrategy('momentum', strategies_config.get('momentum', {}))
        
        # Trading state
        self.initial_capital = trading_config.get('initial_capital', 10000.0)
        self.current_capital = self.initial_capital
        self.running = False
        self.lock = Lock()
        
        # Initialize risk manager
        self.risk_manager.set_capital(self.initial_capital, self.current_capital)
        
        # Trading symbols
        self.symbols = trading_config.get('symbols', [])
        self.scan_interval = trading_config.get('scan_interval', 30)
        
        logger.info(f"[OK] Trading Bot initialized with {len(self.strategies)} strategies")
        logger.info(f"[FEE] Trading type: {self.trading_type}, Maker orders: {self.use_maker_orders}")
        min_tp = self.fee_calculator.get_minimum_take_profit_pct()
        logger.info(f"[FEE] Minimum take-profit: {min_tp:.2f}% (after all costs)")
    
    def _start_price_monitor_handler(self):
        """Handle real-time price monitor signals"""
        handler_thread = Thread(target=self._handle_price_updates, daemon=True)
        handler_thread.start()
        logger.info("[MONITOR] Price monitor handler started")
    
    def _handle_price_updates(self):
        """Process price monitor signals for immediate profit taking"""
        # Handler runs continuously to process monitor signals
        # It checks both bot running state and monitor running state
        while True:
            try:
                # Only process if bot is running AND monitor is running
                if self.running and self.price_monitor.running:
                    # Use get_nowait() to avoid race condition with empty() check
                    # get_nowait() raises Empty exception if queue is empty
                    try:
                        update = self.price_monitor.price_updates.get_nowait()
                        
                        symbol = update['symbol']
                        strategy = update['strategy']
                        signal = update['signal']
                        current_price = update['current_price']
                        
                        if signal == 'TAKE_PROFIT':
                            # IMMEDIATE PROFIT TAKING
                            logger.info(f"[PROFIT TARGET] {symbol} ({strategy}) reached target! Taking profit NOW at ${current_price:.2f}...")
                            self._close_position_immediately(symbol, strategy, current_price, reason='TAKE_PROFIT')
                        
                        elif signal == 'PARTIAL_FEES_PROFIT':
                            # FEES COVERED - PARTIAL CLOSE (Your Smart Idea!)
                            logger.info(f"[PARTIAL FEES] {symbol} ({strategy}) fees covered! Partial closing NOW at ${current_price:.2f}...")
                            self._partial_close_for_fees(symbol, strategy, current_price)
                        
                        elif signal == 'BREAKEVEN_PROFIT':
                            # FEES COVERED + SMALL PROFIT - FULL CLOSE (fallback if partial disabled)
                            logger.info(f"[FEES COVERED] {symbol} ({strategy}) fees covered + small profit! Closing NOW at ${current_price:.2f}...")
                            self._close_position_immediately(symbol, strategy, current_price, reason='FEES_COVERED_PROFIT')
                        
                        elif signal == 'STOP_LOSS':
                            logger.warning(f"[STOP LOSS] {symbol} ({strategy}) hit stop loss! Closing at ${current_price:.2f}...")
                            self._close_position_immediately(symbol, strategy, current_price, reason='STOP_LOSS')
                    except Empty:
                        # Queue is empty, wait a bit
                        time.sleep(0.1)
                else:
                    # Bot or monitor not running, wait longer
                    time.sleep(1.0)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"[ERROR] Error handling price updates: {e}")
                time.sleep(1.0)
    
    def _reload_positions_to_monitor(self):
        """Reload existing open positions into price monitor (for bot restarts)"""
        try:
            open_positions = self.position_manager.get_all_positions()
            if not open_positions:
                return
            
            logger.info(f"[MONITOR] Reloading {len(open_positions)} open positions into price monitor...")
            
            for position in open_positions:
                if position.status != 'OPEN':
                    continue
                
                # Calculate profit/loss percentages from stop_loss and take_profit prices
                if position.action == 'BUY':
                    stop_loss_pct = ((position.entry_price - position.stop_loss) / position.entry_price) * 100.0
                    take_profit_pct = ((position.take_profit - position.entry_price) / position.entry_price) * 100.0
                else:  # SELL (short)
                    stop_loss_pct = ((position.stop_loss - position.entry_price) / position.entry_price) * 100.0
                    take_profit_pct = ((position.entry_price - position.take_profit) / position.entry_price) * 100.0
                
                # Add to monitor
                self.price_monitor.add_position(
                    symbol=position.symbol,
                    strategy=position.strategy,
                    entry_price=position.entry_price,
                    quantity=position.quantity,
                    target_profit_pct=take_profit_pct,
                    stop_loss_pct=stop_loss_pct,
                    action=position.action
                )
                
                logger.info(f"[MONITOR] Reloaded {position.symbol} ({position.strategy}) into monitor")
            
            logger.info(f"[OK] Successfully reloaded {len(open_positions)} positions into price monitor")
            
        except Exception as e:
            logger.error(f"[ERROR] Error reloading positions to monitor: {e}", exc_info=True)
    
    def start(self):
        """Start trading bot"""
        try:
            self.running = True
            logger.info("[START] Starting trading bot...")
            
            # Reload existing open positions into price monitor
            self._reload_positions_to_monitor()
            
            while self.running:
                try:
                    self._trading_cycle()
                    time.sleep(self.scan_interval)
                except KeyboardInterrupt:
                    logger.info("[STOP] Bot stopped by user")
                    break
                except Exception as e:
                    logger.error(f"[ERROR] Error in trading cycle: {e}", exc_info=True)
                    time.sleep(5)  # Wait before retrying
        except Exception as e:
            logger.error(f"[ERROR] Fatal error in bot: {e}", exc_info=True)
            raise
    
    def stop(self):
        """Stop trading bot"""
        self.running = False
        self.price_monitor.stop_monitoring()
        logger.info("[STOP] Trading bot stopped")
    
    def _trading_cycle(self):
        """Execute one trading cycle"""
        try:
            # Check if trading is allowed
            can_trade, reason = self.risk_manager.can_trade()
            if not can_trade:
                logger.warning(f"[WARN] Trading paused: {reason}")
                return
            
            # Scan each symbol
            for symbol in self.symbols:
                try:
                    self._scan_symbol(symbol)
                except Exception as e:
                    logger.error(f"[ERROR] Error scanning {symbol}: {e}")
        except Exception as e:
            logger.error(f"[ERROR] Error in trading cycle: {e}")
    
    def _scan_symbol(self, symbol: str):
        """Scan a symbol for trading opportunities"""
        try:
            # Get market data
            klines = self.market_data.get_klines(symbol)
            if not klines:
                return
            
            closes, highs, lows, volumes, opens = klines
            
            # Calculate indicators
            indicators = IndicatorCalculator.calculate_all(closes, highs, lows, volumes, opens)
            if not indicators:
                return
            
            # Detect market regime
            regime_detector = MarketRegimeDetector()
            market_regime = regime_detector.detect_regime(indicators)
            
            # Get current price
            current_price = self.market_data.get_current_price(symbol)
            if not current_price:
                return
            
            # Check existing positions
            for strategy_name, strategy in self.strategies.items():
                if self.position_manager.has_position(symbol, strategy_name):
                    # Check if position should be closed
                    self._check_position_exit(symbol, strategy_name, current_price)
                else:
                    # Check if new position should be opened
                    self._check_position_entry(symbol, strategy_name, indicators, current_price, market_regime)
        except Exception as e:
            logger.error(f"[ERROR] Error scanning {symbol}: {e}")
    
    def _check_position_entry(
        self,
        symbol: str,
        strategy_name: str,
        indicators: Dict[str, Any],
        price: float,
        market_regime: str
    ):
        """Check if a new position should be opened"""
        try:
            strategy = self.strategies.get(strategy_name)
            if not strategy or not strategy.enabled:
                return
            
            # Check if we can open new position
            current_positions = self.position_manager.get_open_positions_count()
            can_open, reason = self.risk_manager.can_open_position(current_positions)
            if not can_open:
                return
            
            # Generate signal
            signal = strategy.generate_signal(symbol, indicators, price, market_regime)
            if not signal:
                return
            
            # Check confidence threshold
            confidence = signal.get('confidence', 0.0)
            confidence = clamp_value(confidence, 0.0, 100.0)  # Ensure 0-100
            
            if confidence < strategy.confidence_threshold:
                return
            
            # Calculate position size
            quantity = self.risk_manager.calculate_position_size(
                entry_price=price,
                confidence=confidence
            )
            
            if quantity <= 0:
                logger.warning(f"[WARN] Invalid quantity calculated: {quantity}")
                return
            
            # Apply slippage and spread to entry price
            volatility = indicators.get('atr_pct', 0.0) / 100.0  # Convert to 0-1 range
            actual_entry_price = self.slippage_simulator.apply_slippage(
                symbol, price, signal['action'], volatility
            )
            
            # Apply spread
            if signal['action'] == 'BUY':
                actual_entry_price = self.spread_simulator.get_ask_price(actual_entry_price, symbol)
            else:  # SELL
                actual_entry_price = self.spread_simulator.get_bid_price(actual_entry_price, symbol)
            
            # Calculate stop loss and take profit based on actual entry price
            stop_loss_pct = strategy.stop_loss_pct
            take_profit_pct = strategy.take_profit_pct
            
            # Ensure minimum take profit (after fees)
            min_tp_pct = self.fee_calculator.get_minimum_take_profit_pct()
            if take_profit_pct < min_tp_pct:
                logger.warning(f"[WARN] Take profit {take_profit_pct:.2f}% too low, adjusting to {min_tp_pct:.2f}%")
                take_profit_pct = min_tp_pct
            
            stop_loss = self.risk_manager.calculate_stop_loss(
                entry_price=actual_entry_price,
                action=signal['action'],
                custom_pct=stop_loss_pct
            )
            
            take_profit = self.risk_manager.calculate_take_profit(
                entry_price=actual_entry_price,
                action=signal['action'],
                custom_pct=take_profit_pct
            )
            
            # Validate stop loss and take profit
            valid, error = self.risk_manager.validate_stop_loss_take_profit(
                entry_price=actual_entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                action=signal['action']
            )
            
            if not valid:
                logger.warning(f"[WARN] Invalid stop loss/take profit for {symbol}: {error}")
                return
            
            # Open position (paper trading - track only, no API call)
            if self.position_manager.open_position(
                symbol=symbol,
                strategy=strategy_name,
                action=signal['action'],
                entry_price=actual_entry_price,  # Use actual price with slippage/spread
                quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit
            ):
                logger.info(f"[OK] Opened {signal['action']} position: {symbol} @ ${actual_entry_price:.2f} qty={quantity:.6f}")
                logger.info(f"[COSTS] Entry price adjusted: ${price:.2f} -> ${actual_entry_price:.2f} (slippage + spread)")
                
                # Get partial profit taking config
                partial_profit_enabled = trading_config.get('partial_profit_taking', True)
                
                # Add to real-time monitoring for immediate profit taking
                self.price_monitor.add_position(
                    symbol=symbol,
                    strategy=strategy_name,
                    entry_price=actual_entry_price,
                    quantity=quantity,
                    target_profit_pct=take_profit_pct,
                    stop_loss_pct=stop_loss_pct,
                    action=signal['action'],
                    partial_profit_enabled=partial_profit_enabled
                )
        except Exception as e:
            logger.error(f"[ERROR] Error checking position entry: {e}", exc_info=True)
    
    def _close_position_immediately(
        self,
        symbol: str,
        strategy_name: str,
        exit_price: float,
        reason: str = 'TARGET_REACHED'
    ):
        """Close position IMMEDIATELY when target reached (with real costs)"""
        try:
            # Get position
            position = self.position_manager.get_position(symbol, strategy_name)
            if not position or position.status != 'OPEN':
                return
            
            # Remove from monitoring
            self.price_monitor.remove_position(symbol, strategy_name)
            
            # Apply slippage and spread to exit price
            volatility = 0.0  # Could get from current indicators
            exit_action = 'SELL' if position.action == 'BUY' else 'BUY'
            actual_exit_price = self.slippage_simulator.apply_slippage(
                symbol, exit_price, exit_action, volatility
            )
            
            # Apply spread
            if position.action == 'BUY':  # Selling
                actual_exit_price = self.spread_simulator.get_bid_price(actual_exit_price, symbol)
            else:  # SELL position (buying to close)
                actual_exit_price = self.spread_simulator.get_ask_price(actual_exit_price, symbol)
            
            # Calculate profit with ALL costs
            profit_data = self.profit_calculator.calculate_net_profit(
                symbol=symbol,
                entry_price=position.entry_price,
                exit_price=actual_exit_price,
                quantity=position.quantity,
                action=position.action,
                volatility=volatility
            )
            
            # Close position (use actual exit price)
            closed_position = self.position_manager.close_position(
                symbol=symbol,
                strategy=strategy_name,
                exit_price=actual_exit_price,
                exit_reason=reason,
                fees=profit_data['total_costs']  # Include all costs
            )
            
            if closed_position:
                # Update position PnL with net profit (after all costs)
                closed_position.pnl = profit_data['net_profit']
                closed_position.pnl_pct = profit_data['profit_pct']
                
                # Update capital
                self.current_capital += profit_data['net_profit']
                self.risk_manager.record_trade(profit_data['net_profit'])
                self.risk_manager.set_capital(self.initial_capital, self.current_capital)
                
                logger.info(f"[PROFIT TAKEN] {symbol} - Net Profit: ${profit_data['net_profit']:.2f} ({profit_data['profit_pct']:.2f}%)")
                logger.info(f"[COSTS] Entry: ${profit_data['entry_fee']:.2f}, Exit: ${profit_data['exit_fee']:.2f}, "
                          f"Slippage: ${profit_data['entry_slippage'] + profit_data['exit_slippage']:.2f}, "
                          f"Spread: ${profit_data['spread_cost']:.2f}, Total: ${profit_data['total_costs']:.2f}")
                
                # Auto compounding
                if profit_data['net_profit'] > 0:
                    compounded = self.compound_manager.add_profit(profit_data['net_profit'])
                    
                    if compounded > 0:
                        # Compounding triggered! Update capital
                        with self.lock:
                            old_capital = self.current_capital
                            self.current_capital += compounded
                            self.initial_capital = self.current_capital  # Update base
                            
                            # Update risk manager
                            self.risk_manager.set_capital(self.initial_capital, self.current_capital)
                        
                        logger.info(f"[COMPOUND APPLIED] Capital increased: ${old_capital:.2f} → ${self.current_capital:.2f}")
                        logger.info(f"[COMPOUND APPLIED] New trading capital: ${self.current_capital:.2f}")
                        
                        # Save state
                        self.state_manager.set('initial_capital', self.initial_capital)
                        self.state_manager.set('current_capital', self.current_capital)
                
                # Save trade to CSV with complete profit data
                self.trade_storage.save_trade(closed_position, profit_data)
                
        except Exception as e:
            logger.error(f"[ERROR] Error closing position immediately: {e}", exc_info=True)
    
    def _partial_close_for_fees(
        self,
        symbol: str,
        strategy_name: str,
        exit_price: float
    ):
        """Partial close when fees are covered (Your Smart Idea!)"""
        try:
            # Get position
            position = self.position_manager.get_position(symbol, strategy_name)
            if not position or position.status != 'OPEN':
                return
            
            # Get config
            trading_config = self.config.get_trading_config()
            partial_close_pct = trading_config.get('partial_close_pct', 50.0) / 100.0  # Convert to 0-1
            
            # Calculate how much to close (percentage of current quantity)
            close_quantity = position.quantity * partial_close_pct
            
            # Calculate fees for this partial close
            volatility = 0.0
            exit_action = 'SELL' if position.action == 'BUY' else 'BUY'
            
            # Apply slippage and spread
            actual_exit_price = self.slippage_simulator.apply_slippage(
                symbol, exit_price, exit_action, volatility
            )
            if position.action == 'BUY':  # Selling
                actual_exit_price = self.spread_simulator.get_bid_price(actual_exit_price, symbol)
            else:  # SELL position (buying to close)
                actual_exit_price = self.spread_simulator.get_ask_price(actual_exit_price, symbol)
            
            # Calculate fees for partial close
            partial_profit_data = self.profit_calculator.calculate_net_profit(
                symbol=symbol,
                entry_price=position.entry_price,
                exit_price=actual_exit_price,
                quantity=close_quantity,
                action=position.action,
                volatility=volatility
            )
            
            # Partial close
            result = self.position_manager.partial_close_position(
                symbol=symbol,
                strategy=strategy_name,
                close_quantity=close_quantity,
                exit_price=actual_exit_price,
                exit_reason='PARTIAL_FEES_PROFIT',
                fees=partial_profit_data['total_costs']
            )
            
            if result:
                partial_pnl = result['pnl']
                remaining_qty = result['remaining_quantity']
                
                # Update capital with partial profit
                self.current_capital += partial_pnl
                self.risk_manager.record_trade(partial_pnl)
                self.risk_manager.set_capital(self.initial_capital, self.current_capital)
                
                logger.info(f"[PARTIAL CLOSE] {symbol} - Closed {close_quantity:.6f}, P&L: ${partial_pnl:.2f}, Remaining: {remaining_qty:.6f}")
                
                # Update monitor with remaining quantity
                if not result['is_full_close']:
                    # Re-add remaining position to monitor (with updated quantity)
                    position = self.position_manager.get_position(symbol, strategy_name)
                    if position:  # Still has remaining
                        # Calculate percentages from stop/take profit
                        if position.action == 'BUY':
                            stop_loss_pct = ((position.entry_price - position.stop_loss) / position.entry_price) * 100.0
                            take_profit_pct = ((position.take_profit - position.entry_price) / position.entry_price) * 100.0
                        else:
                            stop_loss_pct = ((position.stop_loss - position.entry_price) / position.entry_price) * 100.0
                            take_profit_pct = ((position.entry_price - position.take_profit) / position.entry_price) * 100.0
                        
                        # Remove old monitor entry first
                        self.price_monitor.remove_position(symbol, strategy_name)
                        
                        # Re-add to monitor (will update existing entry)
                        partial_profit_enabled = trading_config.get('partial_profit_taking', True)
                        self.price_monitor.add_position(
                            symbol=symbol,
                            strategy=strategy_name,
                            entry_price=position.entry_price,  # Original entry price
                            quantity=remaining_qty,  # Updated quantity
                            target_profit_pct=take_profit_pct,
                            stop_loss_pct=stop_loss_pct,
                            action=position.action,
                            partial_profit_enabled=False  # Already did partial, wait for target or neutral
                        )
                        logger.info(f"[MONITOR] Updated monitor for remaining {remaining_qty:.6f} of {symbol}")
                
                # Auto compounding
                if partial_pnl > 0:
                    compounded = self.compound_manager.add_profit(partial_pnl)
                    if compounded > 0:
                        with self.lock:
                            old_capital = self.current_capital
                            self.current_capital += compounded
                            self.initial_capital = self.current_capital
                            self.risk_manager.set_capital(self.initial_capital, self.current_capital)
                        logger.info(f"[COMPOUND] Capital: ${old_capital:.2f} → ${self.current_capital:.2f}")
                
                # Save partial close (will save to CSV when fully closed)
                logger.info(f"[PARTIAL SAVED] {symbol} Partial close recorded: ${partial_pnl:.2f}")
            else:
                logger.warning(f"[WARN] Partial close failed for {symbol}")
                
        except Exception as e:
            logger.error(f"[ERROR] Error partial closing for fees: {e}", exc_info=True)
    
    def _check_position_exit(self, symbol: str, strategy_name: str, current_price: float):
        """Check if a position should be closed (backup check in main cycle)"""
        # Real-time monitor handles immediate exits
        # This is just a backup check
        try:
            position = self.position_manager.get_position(symbol, strategy_name)
            if not position or position.status != 'OPEN':
                return
            
            # Check time limit (real-time monitor doesn't check this)
            hold_time = (datetime.now() - position.entry_time).total_seconds() / 60
            strategy = self.strategies.get(strategy_name)
            if strategy and hold_time >= strategy.max_hold_time_minutes:
                logger.info(f"[TIME LIMIT] {symbol} ({strategy_name}) reached max hold time, closing...")
                self._close_position_immediately(symbol, strategy_name, current_price, reason='TIME_LIMIT')
        except Exception as e:
            logger.error(f"[ERROR] Error checking position exit: {e}", exc_info=True)

