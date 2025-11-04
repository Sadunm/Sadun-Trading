# 🔍 Isolated Monitoring System

## Overview
This is a **COMPLETELY ISOLATED** monitoring system for the Sadun Trading Bot. It connects to the bot via API but runs separately, allowing you to monitor and analyze bot performance without affecting the bot itself.

## Features

### ✅ Complete Isolation
- Runs in separate process
- Connects via HTTP API only
- No direct access to bot internals
- Can be stopped/started independently

### 📊 Real-Time Monitoring
- Live statistics (capital, P&L, trades)
- Trade analysis (win rate, profit factor)
- Strategy performance breakdown
- Pattern detection (streaks, best/worst hours)

### 🔗 Connection Management
- Automatic connection checking
- Status indicators
- Error reporting
- Auto-reconnect

## Setup

### 1. Install Dependencies
```bash
pip install requests flask
```

### 2. Start Trading Bot First
```bash
# Make sure bot is running with API server
python main.py
# Bot API should be at http://localhost:10000
```

### 3. Start Monitor
```bash
# Run isolated monitor
python monitor/main.py
# Monitor dashboard at http://localhost:10001
```

## Configuration

Edit `monitor/config.py` to change:
- Bot API URL (default: http://localhost:10000)
- Refresh intervals
- Data storage location

## Usage

1. **Open Dashboard**: http://localhost:10001
2. **View Stats**: Real-time bot statistics
3. **Analyze Trades**: Trade history and analysis
4. **Check Patterns**: Winning/losing streaks, best hours
5. **Monitor Connection**: Connection status and errors

## API Endpoints

### Monitor API (Port 10001)
- `GET /` - Dashboard HTML
- `GET /api/analysis` - Current analysis data
- `GET /api/connection` - Connection status

### Bot API (Port 10000) - Required
- `GET /api/stats` - Bot statistics
- `GET /api/trades` - Trade history
- `GET /api/performance/*` - Performance data

## Architecture

```
┌─────────────────┐
│  Trading Bot    │
│  (Port 10000)   │
└────────┬────────┘
         │ HTTP API
         │
┌────────▼────────┐
│  Monitor System │
│  (Port 10001)   │
│                 │
│  - Connector    │
│  - Analyzer     │
│  - Dashboard    │
└─────────────────┘
```

## Files

- `config.py` - Configuration
- `bot_connector.py` - API connection handler
- `analyzer.py` - Trade analysis logic
- `monitor_service.py` - Main monitoring service
- `dashboard.py` - Web dashboard
- `main.py` - Entry point

## Benefits

1. **Safety**: Monitor doesn't affect bot operation
2. **Flexibility**: Can restart monitor without affecting bot
3. **Analysis**: Deep insights into trading performance
4. **Debugging**: See what bot is doing in real-time
5. **Isolation**: Complete separation of concerns

## Troubleshooting

### Cannot Connect
- Check if bot is running: http://localhost:10000
- Check bot API is accessible
- Verify firewall settings

### No Data
- Wait a few seconds for first data refresh
- Check bot has trades/positions
- Verify API endpoints are working

### Dashboard Not Loading
- Check monitor is running: http://localhost:10001
- Check browser console for errors
- Verify Flask is installed

## Notes

- Monitor runs independently from bot
- Can be stopped/started anytime
- Data is cached for analysis
- Connection status is shown in dashboard

