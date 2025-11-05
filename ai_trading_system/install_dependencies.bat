@echo off
echo ========================================
echo   Installing AI Trading System Dependencies
echo ========================================
echo.

cd /d "%~dp0"
cd ..

echo [INFO] Installing core dependencies...
pip install numpy pandas scikit-learn lightgbm websockets aiohttp requests pyyaml python-dotenv

echo.
echo [INFO] Dependencies installed!
pause
