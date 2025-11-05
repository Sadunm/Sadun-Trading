# Render Deployment Guide

## Quick Deploy to Render

### 1. Prerequisites
- Render account (free tier works)
- Binance Testnet API keys
- OpenRouter API key

### 2. Environment Variables

Set these in Render dashboard:

```
BINANCE_API_KEY=your_testnet_api_key
BINANCE_API_SECRET=your_testnet_secret_key
OPENROUTER_API_KEY=sk-or-v1-your-key
PAPER_TRADING=true
INITIAL_CAPITAL=100.0
```

### 3. Deploy Steps

1. **Connect Repository**
   - Go to Render dashboard
   - Click "New" → "Background Worker"
   - Connect your GitHub repository
   - Select branch: `main`
   - Root directory: `trading_bot/ai_trading_system`

2. **Configure Build**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python main.py`
   - Environment: Python 3.11

3. **Set Environment Variables**
   - Add all variables from step 2

4. **Deploy**
   - Click "Create Background Worker"
   - Wait for build to complete
   - Check logs for startup

### 4. Verify Deployment

Check logs for:
- ✅ `[INIT] All components initialized`
- ✅ `[DATA] Market data stream started`
- ✅ `[AI] Signal generator initialized`
- ✅ `[LOOP] Starting trading loop...`

### 5. Monitor

- **Logs**: View in Render dashboard
- **Trades**: Check log output for `[SIGNAL]` entries
- **Errors**: Monitor for `[ERROR]` entries

### 6. Paper Trading Mode

Bot runs in **paper trading mode** by default:
- No real money
- Simulated trades
- Testnet API only
- Safe for testing

### Troubleshooting

**Build fails:**
- Check Python version (3.11)
- Verify requirements.txt is correct
- Check build logs

**Runtime errors:**
- Verify all environment variables are set
- Check API keys are valid
- Review logs for specific errors

**No signals:**
- Wait for data collection (5-10 minutes)
- Check Binance testnet status
- Verify OpenRouter API key is valid

### Files Structure

```
ai_trading_system/
├── main.py              # Entry point
├── requirements.txt      # Dependencies
├── Procfile             # Render process file
├── runtime.txt          # Python version
├── render.yaml          # Render config
├── .env.example         # Environment template
└── config/
    └── config.yaml      # Configuration
```

### Notes

- Bot runs continuously (Background Worker)
- Auto-restarts on crash
- Logs are persistent
- Free tier: 750 hours/month

