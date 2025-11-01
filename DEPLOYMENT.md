# 🚀 Deployment Guide - Render.com

## GitHub Setup

### 1. Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `badshah-trading-bot` (or any name you prefer)
3. Choose **Public** or **Private**
4. **DO NOT** initialize with README (we already have one)
5. Click "Create repository"

### 2. Push Code to GitHub

```bash
# In your trading_bot directory, run these commands:

# Add remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/badshah-trading-bot.git

# Push to GitHub
git branch -M main
git push -u origin main
```

**Or if you have GitHub CLI:**
```bash
gh repo create badshah-trading-bot --public --source=. --remote=origin --push
```

## Render.com Deployment

### Step 1: Create Render Account

1. Go to https://render.com
2. Sign up with GitHub (easiest way)
3. Connect your GitHub account

### Step 2: Create New Web Service

1. Click **"New +"** → **"Web Service"**
2. **Connect Repository**: Select your `badshah-trading-bot` repository
3. **Configure**:
   - **Name**: `badshah-trading-bot`
   - **Region**: Choose closest to you
   - **Branch**: `main`
   - **Root Directory**: Leave empty (or `trading_bot` if you have nested structure)
   - **Environment**: `Docker`
   - **Dockerfile Path**: `Dockerfile`
   - **Plan**: `Free` (or upgrade if needed)

### Step 3: Set Environment Variables

In Render dashboard, go to **Environment** tab and add:

```
BINANCE_API_KEY=your_testnet_api_key
BINANCE_SECRET_KEY=your_testnet_secret_key
PORT=10000
PYTHONUNBUFFERED=1
```

### Step 4: Deploy

1. Click **"Create Web Service"**
2. Render will automatically:
   - Clone your repository
   - Build Docker image
   - Deploy the service
   - Keep it running 24/7

### Step 5: Access Dashboard

- Your bot will be available at: `https://badshah-trading-bot.onrender.com`
- Dashboard: `https://badshah-trading-bot.onrender.com/`

## Important Notes

### Auto-Deploy

- ✅ Render auto-deploys when you push to `main` branch
- ✅ Bot runs 24/7 (PC doesn't need to be on)
- ✅ Free tier includes 750 hours/month (enough for 24/7)

### Free Tier Limitations

- ⚠️ Service sleeps after 15 minutes of inactivity on free tier
- ⚠️ First request after sleep takes ~30 seconds to wake up
- 💡 **Solution**: Use a cron job or uptime monitor to ping `/api/health` every 14 minutes

### Keep Service Alive (Free Tier)

Add this to your environment variables or use external service:
- Use uptime monitoring service (UptimeRobot, etc.)
- Set it to ping `https://badshah-trading-bot.onrender.com/api/health` every 14 minutes

### Upgrading to Paid Tier

- **Starter Plan** ($7/month): No sleep, always on
- Better for production trading bots

## Monitoring

1. **Logs**: Check Render dashboard → Logs tab
2. **Metrics**: Monitor CPU, Memory, Network
3. **Health**: `/api/health` endpoint

## Troubleshooting

### Service Keeps Restarting
- Check logs in Render dashboard
- Verify API keys are set correctly
- Check if dependencies installed properly

### Bot Not Trading
- Check logs for errors
- Verify API keys are valid
- Check config.yaml settings

### Can't Access Dashboard
- Wait a few minutes after deployment
- Check if service is running (not sleeping)
- Verify PORT is set correctly

## Update Bot

To update your bot:
```bash
# Make changes locally
git add .
git commit -m "Update bot"
git push origin main
```

Render will automatically redeploy! ✨

