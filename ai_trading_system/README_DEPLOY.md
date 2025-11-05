# 🚀 Render Deployment - Complete Setup

## ✅ Pre-Deployment Checklist

### 1. Files Ready
- ✅ `main.py` - Entry point
- ✅ `requirements.txt` - Dependencies (lightweight)
- ✅ `Procfile` - Process definition
- ✅ `runtime.txt` - Python 3.11
- ✅ `render.yaml` - Render config
- ✅ `config/config.yaml` - Configuration
- ✅ `.env.example` - Environment template

### 2. Environment Variables Needed

Set these in Render dashboard:

```bash
# Binance Testnet (for paper trading)
BINANCE_API_KEY=your_testnet_api_key
BINANCE_API_SECRET=your_testnet_secret_key

# OpenRouter (for AI signals)
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Optional
PAPER_TRADING=true
INITIAL_CAPITAL=100.0
```

### 3. Deploy Steps

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Ready for Render deployment"
   git push origin main
   ```

2. **Create Render Service**
   - Go to https://render.com
   - New → Background Worker
   - Connect GitHub repo
   - Settings:
     - **Name**: `ai-trading-bot`
     - **Root Directory**: `trading_bot/ai_trading_system`
     - **Environment**: Python 3
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `python main.py`

3. **Add Environment Variables**
   - Copy from `.env.example`
   - Paste in Render dashboard
   - Save

4. **Deploy**
   - Click "Create Background Worker"
   - Wait for build (2-3 minutes)
   - Check logs

### 4. Verify Deployment

**Success Indicators:**
```
[INIT] Initializing AI Trading Bot...
[INIT] Initialized 4 strategies
[INIT] All components initialized
[DATA] Market data stream started
[AI] Signal generator initialized
[LOOP] Starting trading loop...
```

**Watch for:**
- ✅ No import errors
- ✅ WebSocket connection attempts
- ✅ AI signal generation
- ✅ Data collection

### 5. Monitor

- **Logs**: Real-time in Render dashboard
- **Signals**: Look for `[AI] Generated signal` entries
- **Trades**: Look for `[EXEC] Opened position` entries
- **Errors**: Monitor `[ERROR]` entries

### 6. Paper Trading Mode

✅ **Bot runs in PAPER TRADING mode:**
- Uses Binance **TESTNET** (not real exchange)
- Simulated trades (no real money)
- Safe for testing
- Can run 24/7

### Troubleshooting

**Build Fails:**
- Check Python version (3.11)
- Verify `requirements.txt` syntax
- Check build logs

**Runtime Errors:**
- Verify all env vars are set
- Check API keys are valid
- Review error logs

**No Signals:**
- Wait 5-10 minutes for data collection
- Check Binance testnet status
- Verify OpenRouter API key

**WebSocket Issues:**
- Binance testnet may be down
- Bot will continue with REST API fallback
- Check logs for connection attempts

### Architecture

```
Market Data → Features → AI Analysis → Signals → Validation → Execution
     ↓           ↓           ↓           ↓          ↓           ↓
  WebSocket   Indicators  DeepSeek   AI Signal   Meta AI   Order Exec
     +
  REST API    Technical   OpenAI      Generator   Risk      Paper Trade
```

### Expected Behavior

1. **Startup (0-2 min)**
   - Load config
   - Initialize components
   - Connect WebSocket

2. **Data Collection (2-10 min)**
   - Fetch historical data
   - Start WebSocket stream
   - Calculate indicators

3. **Trading (10+ min)**
   - AI generates signals
   - Meta AI validates
   - Positions allocated
   - Orders executed (paper)

### Files Structure

```
ai_trading_system/
├── main.py                    # Entry point
├── requirements.txt            # Dependencies
├── Procfile                   # Process file
├── runtime.txt                # Python 3.11
├── render.yaml                # Render config
├── DEPLOYMENT.md              # This guide
├── config/
│   └── config.yaml            # Main config
├── strategies/
│   ├── ai_signal_generator.py # AI signal generator
│   └── ...                    # Other strategies
├── data/
│   ├── data_manager.py        # Data handling
│   └── websocket_client.py    # WebSocket
├── features/
│   └── indicators.py           # Technical indicators
└── utils/
    ├── openrouter_client.py   # AI API client
    └── logger.py              # Logging
```

### Support

- Check logs first
- Review `DEPLOYMENT.md` for details
- Verify environment variables
- Test API keys manually

---

**Ready to Deploy! 🚀**

