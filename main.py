"""
Badshah Trading Bot v2.0 - Main Entry Point
"""

import os
import sys
from threading import Thread

# CRITICAL: Add project root to path FIRST
sys.path.insert(0, os.path.dirname(__file__))

# Force unbuffered output
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except:
    pass

# STEP 1: Load .env file FIRST (before logger) - Optional for Render/Cloud
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
        print(f"[DEBUG] .env file loaded from {env_path}")
    else:
        # .env file not found - try to load from environment variables (for Render/Cloud)
        print(f"[INFO] .env file not found at {env_path}, using environment variables")
        # Try loading from current directory (in case of different paths)
        load_dotenv(override=False)  # Load from environment, don't override existing vars
except ImportError:
    print("[WARN] python-dotenv not installed. Using environment variables only.")
except Exception as e:
    print(f"[WARN] Error loading .env: {e}. Continuing with environment variables...")

# STEP 2: Setup logger AFTER .env is loaded
from utils.logger import setup_logger
logger = setup_logger("main")

# STEP 3: Import modules (after logger)
from core.bot import TradingBot
from api.server import run_server
from utils.config_loader import load_config

# STEP 4: Define main function
def main():
    """Main entry point"""
    try:
        logger.info("[INFO] Starting main function...")
        
        # Load configuration
        logger.info("[INFO] Loading configuration...")
        config = load_config()
        logger.info("[INFO] Configuration loaded successfully")
        
        trading_config = config.get_trading_config()
        
        # Get API credentials from environment
        api_key = os.environ.get('BINANCE_API_KEY', '').strip()
        secret_key = os.environ.get('BINANCE_SECRET_KEY', '').strip()
        
        # Validate API keys
        if not api_key or not secret_key:
            logger.error("[ERROR] BINANCE_API_KEY and BINANCE_SECRET_KEY not set!")
            logger.info("Please set them in:")
            logger.info("  - .env file (for local development)")
            logger.info("  - Environment variables (for cloud deployment like Render)")
            logger.info("  - Render Dashboard → Environment tab")
            sys.exit(1)
        
        logger.info(f"[OK] API keys loaded (lengths: {len(api_key)}, {len(secret_key)})")
        
        # Create bot instance
        logger.info("[INFO] Creating TradingBot instance...")
        bot = TradingBot(api_key=api_key, secret_key=secret_key)
        logger.info("[INFO] TradingBot instance created successfully")
        
        # Start Flask server in background
        dashboard_config = config.get_dashboard_config()
        port = dashboard_config.get('port', 10000)
        host = dashboard_config.get('host', '0.0.0.0')
        
        flask_thread = Thread(
            target=run_server,
            args=(bot, port, host),
            daemon=True
        )
        flask_thread.start()
        logger.info(f"[OK] Dashboard started on http://{host}:{port}")
        
        # Start trading bot
        logger.info("[START] Starting trading bot...")
        bot.start()
        
    except KeyboardInterrupt:
        logger.info("[STOP] Bot stopped by user")
    except Exception as e:
        logger.error(f"[ERROR] Fatal error: {e}", exc_info=True)
        sys.exit(1)

# STEP 5: Call main() if script is run directly
if __name__ == '__main__':
    print("[DEBUG] Script execution started")
    print(f"[DEBUG] __name__ = '{__name__}'")
    main()
    print("[DEBUG] Script execution completed")

