"""
Main entry point for Isolated Monitoring System
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitor.dashboard import app
from utils.logger import setup_logger

logger = setup_logger("monitor_main")


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("🔍 SADUN TRADING BOT - ISOLATED MONITOR")
    logger.info("=" * 60)
    logger.info("[INFO] This is a COMPLETELY ISOLATED monitoring system")
    logger.info("[INFO] It connects to the bot via API but is separate")
    logger.info("[INFO] Dashboard: http://localhost:10001")
    logger.info("[INFO] Bot API: http://localhost:10000")
    logger.info("[INFO] Press Ctrl+C to stop")
    logger.info("=" * 60)
    
    try:
        app.run(host='0.0.0.0', port=10001, debug=False)
    except KeyboardInterrupt:
        logger.info("[STOP] Monitor stopped by user")
    except Exception as e:
        logger.error(f"[ERROR] Monitor error: {e}", exc_info=True)
        sys.exit(1)

