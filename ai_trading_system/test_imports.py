"""
Test all imports for AI Trading System
"""
import sys
import os
from pathlib import Path

# Get the script directory
script_dir = Path(__file__).parent.absolute()
# Go up to trading_bot directory
trading_bot_dir = script_dir.parent
# Add to path
sys.path.insert(0, str(trading_bot_dir))

print("=" * 60)
print("Testing AI Trading System Imports")
print("=" * 60)
print()

errors = []

# Test basic imports
print("[1] Testing basic imports...")
try:
    import numpy
    print("  ✅ numpy")
except ImportError as e:
    print(f"  ❌ numpy: {e}")
    errors.append("numpy")

try:
    import pandas
    print("  ✅ pandas")
except ImportError as e:
    print(f"  ❌ pandas: {e}")
    errors.append("pandas")

try:
    import yaml
    print("  ✅ yaml")
except ImportError as e:
    print(f"  ❌ yaml: {e}")
    errors.append("yaml")

try:
    import lightgbm
    print("  ✅ lightgbm")
except ImportError as e:
    print(f"  ❌ lightgbm: {e}")
    errors.append("lightgbm")

try:
    import websockets
    print("  ✅ websockets")
except ImportError as e:
    print(f"  ❌ websockets: {e}")
    errors.append("websockets")

print()

# Test module imports
print("[2] Testing module imports...")

# Add ai_trading_system to path
ai_system_dir = script_dir
sys.path.insert(0, str(ai_system_dir))

try:
    from ai_trading_system.data.data_manager import DataManager
    print("  ✅ DataManager")
except ImportError as e:
    print(f"  ❌ DataManager: {e}")
    errors.append("DataManager")

try:
    from ai_trading_system.features.indicators import IndicatorCalculator
    print("  ✅ IndicatorCalculator")
except ImportError as e:
    print(f"  ❌ IndicatorCalculator: {e}")
    errors.append("IndicatorCalculator")

try:
    from ai_trading_system.strategies.momentum_strategy import MomentumStrategy
    print("  ✅ MomentumStrategy")
except ImportError as e:
    print(f"  ❌ MomentumStrategy: {e}")
    errors.append("MomentumStrategy")

try:
    from ai_trading_system.strategies.mean_reversion_strategy import MeanReversionStrategy
    print("  ✅ MeanReversionStrategy")
except ImportError as e:
    print(f"  ❌ MeanReversionStrategy: {e}")
    errors.append("MeanReversionStrategy")

try:
    from ai_trading_system.strategies.breakout_strategy import BreakoutStrategy
    print("  ✅ BreakoutStrategy")
except ImportError as e:
    print(f"  ❌ BreakoutStrategy: {e}")
    errors.append("BreakoutStrategy")

try:
    from ai_trading_system.strategies.trend_following_strategy import TrendFollowingStrategy
    print("  ✅ TrendFollowingStrategy")
except ImportError as e:
    print(f"  ❌ TrendFollowingStrategy: {e}")
    errors.append("TrendFollowingStrategy")

try:
    from ai_trading_system.strategies.meta_ai_strategy import MetaAIStrategy
    print("  ✅ MetaAIStrategy")
except ImportError as e:
    print(f"  ❌ MetaAIStrategy: {e}")
    errors.append("MetaAIStrategy")

try:
    from ai_trading_system.allocator.position_allocator import PositionAllocator
    print("  ✅ PositionAllocator")
except ImportError as e:
    print(f"  ❌ PositionAllocator: {e}")
    errors.append("PositionAllocator")

try:
    from ai_trading_system.risk.risk_manager import RiskManager
    print("  ✅ RiskManager")
except ImportError as e:
    print(f"  ❌ RiskManager: {e}")
    errors.append("RiskManager")

try:
    from ai_trading_system.execution.order_executor import OrderExecutor
    print("  ✅ OrderExecutor")
except ImportError as e:
    print(f"  ❌ OrderExecutor: {e}")
    errors.append("OrderExecutor")

try:
    from ai_trading_system.utils.openrouter_client import OpenRouterClient
    print("  ✅ OpenRouterClient")
except ImportError as e:
    print(f"  ❌ OpenRouterClient: {e}")
    errors.append("OpenRouterClient")

print()

# Test config
print("[3] Testing config file...")
try:
    import yaml
    config_path = script_dir / "config" / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        print("  ✅ config.yaml loaded")
        api_key = config.get('openrouter', {}).get('api_key', '')
        if api_key and api_key.startswith('sk-or-'):
            print(f"  ✅ OpenRouter API key: Set ({api_key[:20]}...)")
        else:
            print(f"  ⚠️  OpenRouter API key: Missing or invalid")
    else:
        print(f"  ❌ config.yaml not found at {config_path}")
        errors.append("config.yaml")
except Exception as e:
    print(f"  ❌ Error loading config: {e}")
    errors.append("config")

print()
print("=" * 60)
if errors:
    print(f"❌ Found {len(errors)} errors:")
    for error in errors:
        print(f"   - {error}")
    print()
    print("Please fix these errors before running the bot.")
else:
    print("✅ All imports successful!")
    print("✅ System ready to run!")
print("=" * 60)

