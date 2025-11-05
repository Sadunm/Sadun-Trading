#!/usr/bin/env python3
"""
Render-compatible entry point for AI Trading Bot
Handles all startup errors gracefully
"""
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Main entry point with error handling"""
    try:
        # Import main bot
        from main import main as bot_main
        import asyncio
        
        # Run bot
        asyncio.run(bot_main())
        
    except KeyboardInterrupt:
        print("\n[STOP] Bot stopped by user")
        sys.exit(0)
    except ImportError as e:
        print(f"[ERROR] Import error: {e}")
        print(f"[ERROR] Python path: {sys.path}")
        print(f"[ERROR] Current directory: {os.getcwd()}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

