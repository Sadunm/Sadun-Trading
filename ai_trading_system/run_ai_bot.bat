@echo off
REM AI Trading System - Run Script
echo ========================================
echo   Multi-Strategy AI Trading Bot
echo ========================================
echo.

cd /d "%~dp0"
cd ..\..

REM Activate virtual environment if exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo [INFO] Virtual environment activated
)

REM Run the AI trading bot
echo [INFO] Starting AI Trading Bot...
echo [INFO] Working directory: %CD%
echo.
python trading_bot\ai_trading_system\main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Bot exited with error code %ERRORLEVEL%
    pause
)
