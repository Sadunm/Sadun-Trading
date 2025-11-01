# 🤖 Badshah Trading Bot - কিভাবে কাজ করে?

## 📋 সম্পূর্ণ কাজের প্রক্রিয়া (Step by Step)

### 🚀 **1. Bot চালু হওয়ার প্রক্রিয়া**

1. **main.py** চালু হলে:
   - প্রথমে `.env` ফাইল থেকে API keys লোড করে
   - Configuration (`config.yaml`) লোড করে
   - Logger setup করে
   - TradingBot instance তৈরি করে
   - Flask dashboard background এ চালু করে (port 10000)
   - Main trading loop শুরু করে

### 🔄 **2. Main Trading Loop (প্রধান ট্রেডিং চক্র)**

Bot প্রতিটি 30 সেকেন্ডে (configurable) নিচের কাজগুলো করে:

```
START
  ↓
Check if trading allowed (risk management check)
  ↓
For each symbol (BTCUSDT, ETHUSDT, etc.):
  ├─→ Get market data (price, candlesticks)
  ├─→ Calculate technical indicators (RSI, EMA, MACD, etc.)
  ├─→ Detect market regime (uptrend, downtrend, ranging)
  ├─→ For each strategy:
  │   ├─→ Check existing positions
  │   │   ├─→ If position exists: Check exit conditions
  │   │   │   ├─→ Stop loss hit? → Close position
  │   │   │   ├─→ Take profit hit? → Close position
  │   │   │   └─→ Time limit reached? → Close position
  │   │   └─→ If no position: Generate signal
  │   │       ├─→ Strategy analyzes indicators
  │   │       ├─→ If signal found:
  │   │       │   ├─→ Check confidence threshold
  │   │       │   ├─→ Check risk limits (can we trade?)
  │   │       │   ├─→ Calculate position size
  │   │       │   ├─→ Calculate stop loss & take profit
  │   │       │   └─→ Open position (paper trading)
  │   │       └─→ Save position to memory
  └─→ Wait 30 seconds
  ↓
Repeat
```

### 📊 **3. Technical Indicators (টেকনিক্যাল ইন্ডিকেটর)**

Bot প্রতিটি symbol এর জন্য নিচের indicators গণনা করে:

- **RSI (Relative Strength Index)**: 0-100, overbought/oversold বুঝতে
- **EMA 9 & EMA 21**: Moving averages, trend বুঝতে
- **MACD**: Trend momentum বুঝতে
- **Bollinger Bands**: Volatility এবং price levels বুঝতে
- **ATR (Average True Range)**: Volatility measurement
- **Volume Ratio**: Current volume vs average volume
- **Momentum**: Price change percentage

### 🎯 **4. Trading Strategies (ট্রেডিং স্ট্র্যাটেজি)**

#### **A. Scalping Strategy (দ্রুত লাভের জন্য)**
- **Entry Conditions:**
  - RSI < 45 (oversold)
  - Momentum > 0.1% (price rising)
  - Volume > 1.2x average
  - ATR > 0.5% (some volatility)
- **Exit:**
  - Stop Loss: 0.5% loss
  - Take Profit: 1.0% profit
  - Max Hold: 3 hours

#### **B. Day Trading Strategy (দিনে ট্রেড)**
- **Entry Conditions:**
  - EMA 9 > EMA 21 (uptrend) OR EMA 9 < EMA 21 (downtrend)
  - MACD histogram positive/negative
  - Price near Bollinger Band
  - Volume > average
- **Exit:**
  - Stop Loss: 1.0% loss
  - Take Profit: 2.0% profit
  - Max Hold: 24 hours

#### **C. Momentum Strategy (গতি অনুসরণ)**
- **Entry Conditions:**
  - Strong momentum (3-period > 0.5% AND 10-period > 0.3%)
  - MACD confirming trend
  - Volume > 1.1x average
  - RSI not too extreme (< 70 for BUY, > 30 for SELL)
- **Exit:**
  - Stop Loss: 1.5% loss
  - Take Profit: 3.0% profit
  - Max Hold: 8 hours

### 🛡️ **5. Risk Management (ঝুঁকি ব্যবস্থাপনা)**

Bot প্রতিটি ট্রেডের আগে নিচের checks করে:

1. **Daily Trade Limit**: Maximum 20 trades per day
2. **Daily Loss Limit**: যদি দিনে 2% loss হয়, trading বন্ধ
3. **Max Positions**: একসাথে maximum 5 positions
4. **Position Size**: 
   - Minimum: $10 per trade
   - Maximum: $200 per trade
   - Based on confidence: Higher confidence = slightly larger position
5. **Drawdown Protection**: যদি 5% drawdown হয়, emergency stop
6. **Stop Loss/Take Profit Validation**: সবসময় validate করে

### 💾 **6. Data Storage (ডেটা সংরক্ষণ)**

- **Open Positions**: Memory তে রাখে (position_manager)
- **Closed Trades**: CSV file এ saves (`data/trade_history.csv`)
- **Bot State**: JSON file এ saves (`data/bot_state.json`)
- **Logs**: `logs/` folder এ saves (rotation enabled)

### 🌐 **7. Web Dashboard (ওয়েব ড্যাশবোর্ড)**

Flask server port 10000 তে চালু থাকে এবং দেখায়:

- **Current Capital**: এখনকার মূলধন
- **Total P&L**: মোট লাভ/ক্ষতি
- **Open Positions**: খোলা positions সংখ্যা
- **Trade History**: সব trades (open + closed)
- **Real-time Updates**: প্রতি 5 সেকেন্ডে auto-refresh

### 📈 **8. Position Management (পজিশন ব্যবস্থাপনা)**

**Opening Position:**
1. Strategy signal generate করে
2. Confidence threshold check
3. Risk management check
4. Position size calculate
5. Stop loss & take profit calculate
6. Position memory তে add

**Closing Position:**
1. Price check করে:
   - BUY position: Current price <= stop_loss OR >= take_profit
   - SELL position: Current price >= stop_loss OR <= take_profit
2. Time limit check (max hold time)
3. Position close করে
4. P&L calculate করে
5. Capital update করে
6. CSV file এ save করে

### 🔍 **9. Error Handling (ত্রুটি ব্যবস্থাপনা)**

- **API Errors**: Retry logic (3 attempts with exponential backoff)
- **Network Errors**: Automatic retry
- **Data Errors**: Safe defaults return করে
- **Calculation Errors**: All divisions use `safe_divide()` (zero division protection)
- **Validation Errors**: All inputs validated before use
- **All Errors**: Logged to file এবং console

### ⚙️ **10. Configuration (কনফিগারেশন)**

`config/config.yaml` এ আপনি customize করতে পারেন:

- **Trading Symbols**: কোন coins trade করবে
- **Scan Interval**: কত seconds পর পর scan করবে
- **Risk Limits**: Position size, daily limits
- **Strategy Settings**: Confidence thresholds, stop loss/take profit
- **Dashboard Port**: Dashboard কোন port এ চালু হবে

## 🔄 সম্পূর্ণ Flow Diagram

```
[Main.py Starts]
       ↓
[Load .env & Config]
       ↓
[Initialize Bot Components]
       ↓
[Start Dashboard (Background)]
       ↓
[Main Trading Loop Starts]
       ↓
   ┌─────────────────┐
   │  Every 30 sec   │
   └─────────────────┘
       ↓
[Check Risk Limits]
       ↓
[For Each Symbol:]
   ├─→ Get Market Data
   ├─→ Calculate Indicators
   ├─→ Detect Market Regime
   └─→ For Each Strategy:
       ├─→ Has Position? → Check Exit
       └─→ No Position? → Check Entry
       ↓
[Save Trades to CSV]
       ↓
[Update Dashboard]
       ↓
[Wait 30 seconds]
       ↓
[Repeat Loop]
```

## 🎯 Key Features

1. **Multi-Strategy**: 3 strategies simultaneously কাজ করে
2. **Paper Trading**: Real money risk নেই (Testnet)
3. **Risk Management**: Multiple layers of protection
4. **Real-time Dashboard**: Live monitoring
5. **Trade History**: CSV এ সব trades save
6. **Error Recovery**: Automatic retry এবং error handling
7. **Thread-Safe**: Multiple strategies simultaneously safe

## 📝 Example Workflow

**Scenario: BTCUSDT price drops to oversold**

1. Bot scans BTCUSDT (every 30 sec)
2. Gets current price: $50,000
3. Calculates RSI: 42 (oversold)
4. Calculates momentum: +0.2% (rising)
5. Volume ratio: 1.5x (higher than average)
6. **Scalping Strategy** detects opportunity:
   - RSI < 45 ✓
   - Momentum > 0.1 ✓
   - Volume > 1.2 ✓
7. Generates BUY signal with 25% confidence
8. Checks risk limits:
   - Daily trades: 5/20 ✓
   - Current capital: $10,000 ✓
   - Open positions: 2/5 ✓
9. Calculates position:
   - Size: $150 (1.5% of capital)
   - Quantity: 0.003 BTC
   - Stop Loss: $49,750 (0.5% down)
   - Take Profit: $50,500 (1.0% up)
10. Opens position in memory
11. Monitors price:
    - If price hits $50,500 → Close with profit ✓
    - If price hits $49,750 → Close with loss ✗
    - After 3 hours → Force close
12. When closed, saves to CSV and updates capital

## 🔐 Safety Features

- ✅ Paper trading only (no real money)
- ✅ Multiple risk checks before every trade
- ✅ Automatic stop loss on every position
- ✅ Daily loss limits
- ✅ Maximum position limits
- ✅ Drawdown protection
- ✅ Error recovery and logging

## 📊 Monitoring

- **Console Output**: Real-time trading activity
- **Log Files**: Detailed logs in `logs/` folder
- **Dashboard**: Web interface at http://localhost:10000
- **CSV Files**: Trade history in `data/trade_history.csv`

---

**এই bot সম্পূর্ণ automation-এ কাজ করে - আপনার interference প্রয়োজন নেই!**


