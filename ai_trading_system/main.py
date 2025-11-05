"""
Main Trading Bot Orchestrator - Multi-Strategy AI System
"""
import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, Any

# COMPLETE ISOLATION: Only use ai_trading_system package
# No imports from parent trading_bot directory
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

# Import from ai_trading_system package (relative imports)
from data.data_manager import DataManager
from features.indicators import IndicatorCalculator
from strategies.momentum_strategy import MomentumStrategy
from strategies.mean_reversion_strategy import MeanReversionStrategy
from strategies.breakout_strategy import BreakoutStrategy
from strategies.trend_following_strategy import TrendFollowingStrategy
from strategies.meta_ai_strategy import MetaAIStrategy
from allocator.position_allocator import PositionAllocator
from risk.risk_manager import RiskManager
from execution.order_executor import OrderExecutor
from utils.openrouter_client import OpenRouterClient
import yaml
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Use only ai_trading_system logger (no parent dependency)
try:
    from utils.logger import setup_logger
except ImportError:
    # Fallback logger setup
    def setup_logger(name="bot", log_level="INFO"):
        os.makedirs('logs', exist_ok=True)
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        logger.handlers.clear()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        log_filename = f"logs/ai_bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = RotatingFileHandler(log_filename, maxBytes=10*1024*1024, backupCount=3, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        return logger

logger = setup_logger("main_bot")


class AITradingBot:
    """Main AI Trading Bot"""
    
    def __init__(self, config_path: str = None):
        # Determine config path
        if config_path is None:
            # Try relative to script location
            script_dir = Path(__file__).parent
            config_path = script_dir / "config" / "config.yaml"
            if not config_path.exists():
                # Try parent directory
                config_path = script_dir.parent / "ai_trading_system" / "config" / "config.yaml"
        
        # Load config
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_content = f.read()
                # Replace environment variables in config
                import re
                env_pattern = r'\$\{([^}]+)\}'
                def replace_env(match):
                    env_var = match.group(1)
                    env_value = os.getenv(env_var)
                    if env_value is None:
                        # If env var not set, try to use default or warn
                        logger.warning(f"[WARN] Environment variable {env_var} not set, using placeholder")
                        return match.group(0)  # Keep placeholder
                    return env_value
                config_content = re.sub(env_pattern, replace_env, config_content)
                self.config = yaml.safe_load(config_content)
        except Exception as e:
            logger.error(f"[ERROR] Failed to load config: {e}")
            raise
        
        # Initialize components
        self.data_manager = None
        self.strategies = {}
        self.allocator = None
        self.risk_manager = None
        self.order_executor = None
        self.meta_ai = None
        
        # State
        self.running = False
        self.capital = self.config.get('trading', {}).get('initial_capital', 100.0)
        self.positions = []  # List of open positions
        self.closed_positions = []  # Trade history
        self.total_pnl = 0.0  # Total profit/loss
        
    async def initialize(self):
        """Initialize all components"""
        logger.info("[INIT] Initializing AI Trading Bot...")
        logger.info(f"[INIT] Working directory: {os.getcwd()}")
        logger.info(f"[INIT] Python version: {sys.version}")
        
        try:
            # 1. Data Manager
            exchange = self.config.get('exchange', {}).get('name', 'binance')
            symbols = self.config.get('data', {}).get('symbols', [])
            websocket_url = self.config.get('exchange', {}).get('websocket_url', {}).get(exchange)
            
            self.data_manager = DataManager(
                exchange=exchange,
                symbols=symbols,
                websocket_url=websocket_url,
                store_local=self.config.get('data', {}).get('store_local', True),
                data_dir=self.config.get('data', {}).get('data_dir', 'ai_trading_system/data/storage')
            )
            
            # 2. Strategies
            strategy_configs = self.config.get('strategies', {})
            
            if strategy_configs.get('momentum', {}).get('enabled', True):
                self.strategies['momentum'] = MomentumStrategy('momentum', strategy_configs.get('momentum', {}))
            
            if strategy_configs.get('mean_reversion', {}).get('enabled', True):
                self.strategies['mean_reversion'] = MeanReversionStrategy('mean_reversion', strategy_configs.get('mean_reversion', {}))
            
            if strategy_configs.get('breakout', {}).get('enabled', True):
                self.strategies['breakout'] = BreakoutStrategy('breakout', strategy_configs.get('breakout', {}))
            
            if strategy_configs.get('trend_following', {}).get('enabled', True):
                self.strategies['trend_following'] = TrendFollowingStrategy('trend_following', strategy_configs.get('trend_following', {}))
            
            if strategy_configs.get('meta_ai', {}).get('enabled', True):
                self.meta_ai = MetaAIStrategy('meta_ai', strategy_configs.get('meta_ai', {}))
            
            logger.info(f"[INIT] Initialized {len(self.strategies)} strategies")
            
            # 3. Allocator
            self.allocator = PositionAllocator(self.config)
            
            # 4. Risk Manager
            self.risk_manager = RiskManager(self.config)
            self.risk_manager.initialize(self.capital)
            
            # 5. Order Executor
            # Note: In production, pass actual API client
            self.order_executor = OrderExecutor(self.config, api_client=None)
            
            logger.info("[INIT] All components initialized")
            
        except Exception as e:
            logger.error(f"[ERROR] Initialization failed: {e}", exc_info=True)
            # Don't raise - try to continue with partial initialization
            logger.warning("[WARN] Continuing with partial initialization. Some features may not work.")
    
    async def start(self):
        """Start trading bot"""
        logger.info("[START] Starting AI Trading Bot...")
        
        try:
            # Start data manager
            await self.data_manager.start()
            
            self.running = True
            
            # Main trading loop
            await self._trading_loop()
            
        except KeyboardInterrupt:
            logger.info("[STOP] Bot stopped by user")
        except asyncio.CancelledError:
            logger.info("[STOP] Bot cancelled")
        except Exception as e:
            logger.error(f"[ERROR] Bot error: {e}", exc_info=True)
        finally:
            await self.stop()
    
    async def _trading_loop(self):
        """Main trading loop"""
        logger.info("[LOOP] Starting trading loop...")
        
        # Wait a bit for WebSocket to stabilize
        await asyncio.sleep(5)
        
        while self.running:
            try:
                # CRITICAL: Monitor open positions first (stop loss/take profit)
                await self._monitor_positions()
                
                # Process each symbol for new signals
                symbols = self.config.get('data', {}).get('symbols', [])
                
                for symbol in symbols:
                    await self._process_symbol(symbol)
                
                # Wait before next iteration
                await asyncio.sleep(30)  # 30 second intervals
                
            except asyncio.CancelledError:
                logger.info("[LOOP] Trading loop cancelled")
                break
            except Exception as e:
                logger.error(f"[ERROR] Error in trading loop: {e}", exc_info=True)
                await asyncio.sleep(5)
    
    async def _monitor_positions(self):
        """Monitor open positions for stop loss/take profit"""
        if not self.positions:
            return
        
        try:
            positions_to_close = []
            
            for position in self.positions:
                symbol = position.get('symbol')
                action = position.get('action')
                entry_price = position.get('executed_price') or position.get('entry_price', 0)
                stop_loss = position.get('stop_loss', 0)
                take_profit = position.get('take_profit', 0)
                quantity = position.get('executed_quantity') or position.get('position_size', 0)
                
                if entry_price <= 0:
                    continue
                
                # Get current price
                current_price = self.data_manager.get_current_price(symbol)
                if not current_price or current_price <= 0:
                    continue
                
                # Calculate P&L
                if action == 'LONG':
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100
                    # Check stop loss
                    if stop_loss > 0 and current_price <= stop_loss:
                        positions_to_close.append({
                            'position': position,
                            'reason': 'STOP_LOSS',
                            'exit_price': stop_loss,
                            'pnl_pct': ((stop_loss - entry_price) / entry_price) * 100
                        })
                    # Check take profit
                    elif take_profit > 0 and current_price >= take_profit:
                        positions_to_close.append({
                            'position': position,
                            'reason': 'TAKE_PROFIT',
                            'exit_price': take_profit,
                            'pnl_pct': ((take_profit - entry_price) / entry_price) * 100
                        })
                elif action == 'SHORT':
                    pnl_pct = ((entry_price - current_price) / entry_price) * 100
                    # Check stop loss
                    if stop_loss > 0 and current_price >= stop_loss:
                        positions_to_close.append({
                            'position': position,
                            'reason': 'STOP_LOSS',
                            'exit_price': stop_loss,
                            'pnl_pct': ((entry_price - stop_loss) / entry_price) * 100
                        })
                    # Check take profit
                    elif take_profit > 0 and current_price <= take_profit:
                        positions_to_close.append({
                            'position': position,
                            'reason': 'TAKE_PROFIT',
                            'exit_price': take_profit,
                            'pnl_pct': ((entry_price - take_profit) / entry_price) * 100
                        })
            
            # Close positions
            for close_info in positions_to_close:
                await self._close_position(close_info['position'], close_info['exit_price'], close_info['reason'], close_info['pnl_pct'])
                
        except Exception as e:
            logger.error(f"[ERROR] Error monitoring positions: {e}", exc_info=True)
    
    async def _close_position(self, position: Dict[str, Any], exit_price: float, reason: str, pnl_pct: float):
        """Close a position"""
        try:
            symbol = position.get('symbol')
            action = position.get('action')
            entry_price = position.get('executed_price') or position.get('entry_price', 0)
            quantity = position.get('executed_quantity') or position.get('position_size', 0)
            
            # Calculate P&L
            if action == 'LONG':
                gross_pnl = (exit_price - entry_price) * quantity
            else:  # SHORT
                gross_pnl = (entry_price - exit_price) * quantity
            
            # Estimate fees (0.1% each side for Binance)
            entry_fee = entry_price * quantity * 0.001
            exit_fee = exit_price * quantity * 0.001
            total_fees = entry_fee + exit_fee
            
            net_pnl = gross_pnl - total_fees
            net_pnl_pct = (net_pnl / (entry_price * quantity)) * 100 if entry_price * quantity > 0 else 0
            
            # Update capital
            self.capital += net_pnl
            self.total_pnl += net_pnl
            
            # Record trade
            trade_record = {
                'symbol': symbol,
                'strategy': position.get('strategy', 'unknown'),
                'action': action,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'quantity': quantity,
                'entry_time': position.get('entry_time', datetime.now().isoformat()),
                'exit_time': datetime.now().isoformat(),
                'gross_pnl': gross_pnl,
                'fees': total_fees,
                'net_pnl': net_pnl,
                'pnl_pct': net_pnl_pct,
                'reason': reason,
                'status': 'CLOSED'
            }
            
            # Remove from open positions
            if position in self.positions:
                self.positions.remove(position)
            
            # Add to closed positions
            self.closed_positions.append(trade_record)
            
            # Record in risk manager
            self.risk_manager.record_trade(trade_record)
            
            logger.info(f"[CLOSE] {symbol} {action} @ {exit_price:.2f} | "
                       f"P&L: {net_pnl:.2f} ({net_pnl_pct:.2f}%) | Reason: {reason}")
            
        except Exception as e:
            logger.error(f"[ERROR] Error closing position: {e}", exc_info=True)
    
    async def _process_symbol(self, symbol: str):
        """Process a single symbol"""
        try:
            # Get market data
            ohlcv_data = self.data_manager.get_ohlcv(symbol, limit=200)
            
            # Reduced requirement - allow trading with less data if WebSocket is working
            if len(ohlcv_data) < 20:
                logger.debug(f"[DEBUG] Insufficient data for {symbol}: {len(ohlcv_data)} candles (need 20)")
                return
            
            # Build features
            features = IndicatorCalculator.build_features(ohlcv_data)
            
            if not features:
                return
            
            # Get current price
            current_price = self.data_manager.get_current_price(symbol)
            if not current_price:
                return
            
            # Generate signals from all strategies
            signals = []
            
            # 1. AI Signal Generator (PRIMARY - uses DeepSeek to generate signals)
            try:
                # Lazy import to avoid circular dependencies
                if not hasattr(self, 'ai_generator'):
                    try:
                        from ai_trading_system.strategies.ai_signal_generator import AISignalGenerator
                        self.ai_generator = AISignalGenerator()
                        logger.info("[AI] Signal generator initialized")
                    except Exception as e:
                        logger.warning(f"[WARN] Failed to initialize AI generator: {e}. Continuing without AI signals.")
                        self.ai_generator = None
                
                if self.ai_generator:
                    # Add timeout to AI signal generation (30s timeout)
                    try:
                        # Use asyncio.to_thread for sync function (Python 3.9+)
                        # For older Python, use loop.run_in_executor
                        try:
                            ai_signal = await asyncio.wait_for(
                                asyncio.to_thread(
                                    self.ai_generator.generate_signal,
                                    symbol=symbol,
                                    features=features,
                                    current_price=current_price,
                                    ohlcv_data=ohlcv_data
                                ),
                                timeout=30.0  # 30 second timeout
                            )
                        except AttributeError:
                            # Python < 3.9 fallback
                            loop = asyncio.get_event_loop()
                            ai_signal = await asyncio.wait_for(
                                loop.run_in_executor(
                                    None,
                                    lambda: self.ai_generator.generate_signal(
                                        symbol=symbol,
                                        features=features,
                                        current_price=current_price,
                                        ohlcv_data=ohlcv_data
                                    )
                                ),
                                timeout=30.0
                            )
                    except asyncio.TimeoutError:
                        logger.warning(f"[WARN] AI signal generation timeout for {symbol} (30s), using fallback")
                        ai_signal = None
                    except Exception as e:
                        logger.error(f"[ERROR] AI signal generation error for {symbol}: {e}")
                        ai_signal = None
                    
                    if ai_signal and ai_signal.get('action') != 'FLAT':
                        ai_signal['symbol'] = symbol
                        ai_signal['strategy'] = 'ai_generator'
                        signals.append(ai_signal)
                        logger.info(f"[AI] Generated signal for {symbol}: {ai_signal.get('action')} "
                                   f"(confidence: {ai_signal.get('confidence', 0):.2%})")
                    
            except Exception as e:
                logger.error(f"[ERROR] Error in AI signal generation for {symbol}: {e}", exc_info=True)
            
            # 2. Rule-based strategies (SECONDARY - fallback)
            for strategy_name, strategy in self.strategies.items():
                # Skip meta_ai (it's for validation, not signal generation)
                if strategy_name == 'meta_ai':
                    continue
                    
                try:
                    signal = strategy.generate_signal(
                        symbol=symbol,
                        features=features,
                        current_price=current_price
                    )
                    
                    if signal and strategy.validate_signal(signal):
                        signal['symbol'] = symbol
                        signal['strategy'] = strategy_name
                        signals.append(signal)
                        
                except Exception as e:
                    logger.error(f"[ERROR] Error in {strategy_name} for {symbol}: {e}")
            
            # Meta AI validation
            if self.meta_ai and signals:
                validated_signals = []
                for signal in signals:
                    validation = self.meta_ai.validate_signal(
                        signal=signal,
                        symbol=symbol,
                        features=features,
                        current_price=current_price
                    )
                    
                    if validation.get('approved', True):
                        # Update confidence with AI validation
                        signal['confidence'] = validation.get('confidence', signal.get('confidence', 0.0))
                        validated_signals.append(signal)
                    else:
                        logger.info(f"[FILTER] {symbol} {signal.get('strategy')} rejected by AI: {validation.get('warnings', [])}")
                
                signals = validated_signals
            
            # Allocate positions
            if signals:
                allocated = self.allocator.allocate(
                    signals=signals,
                    capital=self.capital,
                    current_positions=self.positions
                )
                
                # Execute positions
                for position in allocated:
                    await self._execute_position(position)
            
        except Exception as e:
            logger.error(f"[ERROR] Error processing {symbol}: {e}", exc_info=True)
    
    async def _execute_position(self, position: Dict[str, Any]):
        """Execute a position"""
        try:
            symbol = position.get('symbol')
            action = position.get('action')
            quantity = position.get('position_size', 0)
            entry_price = position.get('entry_price', 0)
            
            # Risk check
            can_open, reason = self.risk_manager.can_open_position(
                position_size=quantity,
                entry_price=entry_price,
                stop_loss=position.get('stop_loss', 0),
                current_positions=self.positions
            )
            
            if not can_open:
                logger.info(f"[RISK] Position rejected: {reason}")
                return
            
            # Generate order ID
            import time
            order_id = self.order_executor.generate_order_id(symbol, action, time.time())
            
            # Execute order
            result = await self.order_executor.execute_order(
                symbol=symbol,
                action=action,
                quantity=quantity,
                entry_price=entry_price,
                order_id=order_id
            )
            
            if result.get('success'):
                # Add position with entry time
                self.positions.append({
                    **position,
                    'order_id': order_id,
                    'executed_price': result.get('executed_price'),
                    'executed_quantity': result.get('executed_quantity'),
                    'entry_time': datetime.now().isoformat(),
                    'status': 'OPEN'
                })
                
                logger.info(f"[EXEC] Opened {action} position: {symbol} {quantity:.8f} @ ${result.get('executed_price'):.2f}")
            else:
                logger.warning(f"[WARN] Order failed: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"[ERROR] Error executing position: {e}", exc_info=True)
    
    async def stop(self):
        """Stop trading bot"""
        logger.info("[STOP] Stopping bot...")
        self.running = False
        
        if self.data_manager:
            await self.data_manager.stop()
        
        logger.info("[STOP] Bot stopped")


async def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("[START] Multi-Strategy AI Trading Bot")
    logger.info("=" * 60)
    
    bot = AITradingBot()
    
    try:
        await bot.initialize()
        await bot.start()
    except KeyboardInterrupt:
        logger.info("[STOP] Interrupted by user")
    except Exception as e:
        logger.error(f"[ERROR] Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[STOP] Bot stopped by user")
    except Exception as e:
        print(f"[ERROR] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

