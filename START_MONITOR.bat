@echo off
echo ============================================
echo Starting Isolated Monitor System
echo ============================================
echo.
echo Make sure Trading Bot is running first!
echo Bot API: http://localhost:10000
echo Monitor: http://localhost:10001
echo.
python monitor/main.py
pause

