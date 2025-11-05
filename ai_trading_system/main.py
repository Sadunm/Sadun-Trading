"""
Main Trading Bot Orchestrator - Multi-Strategy AI System
"""
import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path
script_dir = Path(__file__).parent
trading_bot_dir = script_dir.parent
sys.path.insert(0, str(trading_bot_dir))

# Import from ai_trading_system package
from ai_trading_system.data.data_manager import DataManager
from ai_trading_system.features.indicators import IndicatorCalculator
from ai_trading_system.strategies.momentum_strategy import MomentumStrategy
from ai_trading_system.strategies.mean_reversion_strategy import MeanReversionStrategy
from ai_trading_system.strategies.breakout_strategy import BreakoutStrategy
from ai_trading_system.strategies.trend_following_strategy import TrendFollowingStrategy
from ai_trading_system.strategies.meta_ai_strategy import MetaAIStrategy
from ai_trading_system.allocator.position_allocator import PositionAllocator
from ai_trading_system.risk.risk_manager import RiskManager
from ai_trading_system.execution.order_executor import OrderExecutor
from ai_trading_system.utils.openrouter_client import OpenRouterClient
import yaml
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Import logger from parent utils
sys.path.insert(0, str(Path(__file__).parent.parent))
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
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
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
        self.positions = []
        
    async def initialize(self):
        """Initialize all components"""
        logger.info("[INIT] Initializing AI Trading Bot...")
        
        try:
            # 1. Data Manager
            exchange = self.config.get('exchange', {}).get('name', 'bybit')
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
            raise
    
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
        
        # Wait for initial data collection (5 minutes worth of data)
        logger.info("[LOOP] Waiting for initial data collection (5 minutes)...")
        await asyncio.sleep(60)  # Wait 1 minute for initial candles
        
        while self.running:
            try:
                # Process each symbol
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
    
    async def _process_symbol(self, symbol: str):
        """Process a single symbol"""
        try:
            # Get market data
            ohlcv_data = self.data_manager.get_ohlcv(symbol, limit=200)
            
            if len(ohlcv_data) < 50:
                logger.debug(f"[DEBUG] Insufficient data for {symbol}: {len(ohlcv_data)} candles (need 50)")
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
            
            for strategy_name, strategy in self.strategies.items():
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
                # Add position
                self.positions.append({
                    **position,
                    'order_id': order_id,
                    'executed_price': result.get('executed_price'),
                    'executed_quantity': result.get('executed_quantity'),
                    'status': 'OPEN'
                })
                
                logger.info(f"[EXEC] Opened {action} position: {symbol} {quantity} @ {result.get('executed_price')}")
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
    asyncio.run(main())

