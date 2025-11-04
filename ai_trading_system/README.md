# Multi-Strategy AI Trading System

## 🚀 Overview

Production-grade multi-strategy AI trading system with:
- **5 Independent Strategies**: Momentum, Mean Reversion, Breakout, Trend Following, Meta AI
- **ML Models**: LightGBM, TFT (Temporal Fusion Transformer)
- **LLM Integration**: OpenRouter API for risk filtering
- **Advanced Execution**: TWAP/VWAP order slicing
- **Comprehensive Risk Management**: Portfolio-level risk control
- **Real-time Data**: WebSocket market data streaming

## 📁 Architecture

```
ai_trading_system/
├── config/              # Configuration files
├── data/                # Data layer (WebSocket, storage)
├── features/            # Feature engineering & indicators
├── models/              # ML models (LightGBM, TFT)
├── strategies/          # Trading strategies
├── allocator/           # Position allocator
├── risk/                # Risk management
├── execution/           # Order execution engine
├── backtesting/         # Backtesting engine
└── utils/               # Utilities
```

## 🎯 Strategies

### 1. Momentum Strategy
- **Model**: LightGBM
- **Features**: Returns, RSI, MACD, volume spikes
- **Output**: Long/Short/Flat + confidence

### 2. Mean Reversion
- **Method**: Z-score + Bollinger Bands
- **Entry**: Statistical edges only
- **Filter**: LightGBM validation

### 3. Breakout Strategy
- **Method**: ATR breakout detection
- **Trigger**: Volatility expansion
- **SL/TP**: Dynamic based on ATR

### 4. Trend Following
- **Model**: TFT (Temporal Fusion Transformer)
- **Forecast**: Next 1, 4, 12, 24 bars
- **Sizing**: Based on forecast slope/intensity

### 5. Meta AI Strategy
- **Purpose**: Risk filtering only (NOT signal generation)
- **LLM**: OpenRouter models
- **Checks**: Risk review, news, anomaly detection

## 🔧 Setup

### 1. Install Dependencies
```bash
pip install -r ai_trading_system/requirements.txt
```

### 2. Configure
Edit `ai_trading_system/config/config.yaml`:
- OpenRouter API key
- Exchange credentials
- Strategy parameters
- Risk limits

### 3. Run
```bash
python ai_trading_system/main.py
```

## 📊 Features

### Data Layer
- Real-time WebSocket streaming
- Orderbook depth tracking
- Local data storage
- Automatic retry/backoff

### Feature Engineering
- 30+ technical indicators
- Volatility normalization
- ML-ready features
- Real-time calculation

### Risk Management
- Max 1% risk per trade
- Max 20% portfolio risk
- ATR-based stop loss
- Volatility targeting
- Drawdown protection

### Execution
- TWAP/VWAP order slicing
- Slippage limits
- Spread filtering
- Order idempotency
- Partial fill handling

## 🧪 Backtesting

Vectorized backtesting engine with:
- Correct fee/slippage modeling
- Walk-forward training
- Equity curve analysis
- Performance metrics (Sharpe, Sortino, Calmar)

## 📝 Logging

JSON-structured logs:
- Trade history
- Signal logs
- Error tracking
- Latency metrics
- Performance analytics

## ⚠️ Important Notes

1. **Meta AI Strategy**: Does NOT generate signals, only filters/validates
2. **OpenRouter Integration**: Fail-open design (approves if AI unavailable)
3. **No Duplicate Trades**: Order idempotency ensures no duplicates
4. **Risk First**: All trades checked against risk limits before execution

## 🚨 Production Readiness

- ✅ Full error handling
- ✅ No calculation errors
- ✅ No duplicate trades
- ✅ No random trades
- ✅ Spread/fee/slippage handling
- ✅ Auto-recovery
- ✅ Comprehensive logging
- ✅ Kill-switch safety

## 📚 Documentation

See individual module docstrings for detailed API documentation.

