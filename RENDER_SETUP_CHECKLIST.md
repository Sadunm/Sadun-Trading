# ✅ Render Setup Checklist

## Important Settings:

### 1. ✅ Source Code
- **Source**: `Sadunm/Sadun-Trading` ✓

### 2. ✅ Basic Settings
- **Name**: `Sadun-Trading` ✓
- **Language**: `Docker` ✓
- **Branch**: `main` ✓
- **Region**: `Singapore` ✓ (or choose closest)

### 3. ⚠️ Root Directory
- **Root Directory**: Leave **EMPTY** (or set to `.` if files are in root)
- **OR** if your files are in `trading_bot/` folder, set to: `trading_bot`

### 4. ✅ Docker Settings
- **Dockerfile Path**: `.` (or `Dockerfile` if in root)
- **Docker Build Context**: `.` (default)

### 5. ⚠️ Health Check Path
- **Current**: `/healthz` ❌
- **Should be**: `/api/health` ✅

### 6. ⚠️ Environment Variables (CRITICAL!)
Add these two:
```
BINANCE_API_KEY = your_testnet_api_key
BINANCE_SECRET_KEY = your_testnet_secret_key
```

Also add:
```
PYTHONUNBUFFERED = 1
PORT = 10000
```

### 7. ⚠️ Instance Type
- **Current**: Free (will sleep after 15 min inactivity)
- **Recommendation**: 
  - Free is OK for testing
  - For 24/7 trading, upgrade to **Starter ($7/month)** - no sleep

### 8. ✅ Auto-Deploy
- **Auto-Deploy**: ON ✓ (keep enabled)

## After Deployment:

1. ✅ Check logs for errors
2. ✅ Verify dashboard accessible: `https://sadun-trading.onrender.com`
3. ✅ Monitor first few trades
4. ✅ Check environment variables are loaded

## Free Tier Sleep Issue:

If using Free tier:
- Service sleeps after 15 min inactivity
- First request wakes it up (~30 sec delay)
- **Solution**: Use external uptime monitor to ping `/api/health` every 14 min

## Paid Tier Benefits:

**Starter ($7/month)**:
- ✅ Always on (no sleep)
- ✅ Better for trading bots
- ✅ 0.5 CPU, 512 MB RAM

