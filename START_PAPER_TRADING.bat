@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo BADSHAH TRADING BOT v2.0
echo Paper Trading Mode
echo ========================================
echo.

REM Check for virtual environment
if exist "venv\Scripts\python.exe" (
    echo [OK] Found virtual environment: venv
    set "PYTHON_CMD=venv\Scripts\python.exe"
) else if exist "env\Scripts\python.exe" (
    echo [OK] Found virtual environment: env
    set "PYTHON_CMD=env\Scripts\python.exe"
) else (
    echo No virtual environment found. Using system Python.
    set "PYTHON_CMD=python"
)

REM Set environment variables
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
set PORT=10000

REM Check for .env file
if exist ".env" (
    echo [OK] Found .env file - API keys will be loaded from .env file
) else (
    echo [WARN] No .env file found
    echo Please create .env file with:
    echo   BINANCE_API_KEY=your_key
    echo   BINANCE_SECRET_KEY=your_secret
    echo.
)

echo Installing dependencies...
%PYTHON_CMD% -m pip install -q -r requirements.txt

echo.
echo Starting Badshah Trading Bot v2.0...
echo Dashboard will be available at: http://localhost:10000
echo Press Ctrl+C to stop
echo.

REM Run the bot
cd /d "%~dp0"
%PYTHON_CMD% main.py

pause

