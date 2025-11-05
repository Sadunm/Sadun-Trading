"""
Test initialization of AI Trading Bot
"""
import sys
import asyncio
from pathlib import Path

# Add parent directory to path
script_dir = Path(__file__).parent
trading_bot_dir = script_dir.parent
sys.path.insert(0, str(trading_bot_dir))

print("=" * 60)
print("Testing AI Trading Bot Initialization")
print("=" * 60)
print()

async def test_init():
    """Test bot initialization"""
    try:
        # Import bot
        print("[1] Importing AITradingBot...")
        from ai_trading_system.main import AITradingBot
        print("  ✅ Import successful")
        
        print()
        print("[2] Creating bot instance...")
        bot = AITradingBot()
        print("  ✅ Bot instance created")
        print(f"  ✅ Config loaded: {len(bot.config)} sections")
        print(f"  ✅ Initial capital: ${bot.capital:.2f}")
        
        print()
        print("[3] Initializing components...")
        await bot.initialize()
        print("  ✅ All components initialized")
        print(f"  ✅ Strategies: {len(bot.strategies)}")
        print(f"  ✅ Data manager: {'Ready' if bot.data_manager else 'None'}")
        print(f"  ✅ Risk manager: {'Ready' if bot.risk_manager else 'None'}")
        print(f"  ✅ Order executor: {'Ready' if bot.order_executor else 'None'}")
        print(f"  ✅ Meta AI: {'Ready' if bot.meta_ai else 'None'}")
        
        print()
        print("=" * 60)
        print("✅ INITIALIZATION SUCCESSFUL!")
        print("=" * 60)
        print()
        print("Bot is ready to run. Use Ctrl+C to stop.")
        print()
        
        # Stop bot
        await bot.stop()
        
    except FileNotFoundError as e:
        print(f"  ❌ Config file not found: {e}")
        print()
        print("Please check config.yaml path")
        return False
    except Exception as e:
        print(f"  ❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    try:
        result = asyncio.run(test_init())
        if not result:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n[STOP] Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

