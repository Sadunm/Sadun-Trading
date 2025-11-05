@echo off
echo Testing AI Trading System Imports...
echo.
cd /d "%~dp0"
cd ..\..
python trading_bot\ai_trading_system\test_imports.py
pause

