@echo off
echo Testing AI Trading Bot Initialization...
echo.
cd /d "%~dp0"
cd ..\..
python trading_bot\ai_trading_system\test_init.py
pause

