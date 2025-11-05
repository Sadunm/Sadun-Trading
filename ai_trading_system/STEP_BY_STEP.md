# 🚀 Step-by-Step Setup Guide

## ✅ STEP 1: Dependencies Installed
আপনি dependencies install করেছেন:
- ✅ numpy
- ✅ pandas  
- ✅ lightgbm
- ✅ websockets
- ✅ requests
- ✅ pyyaml

## 📋 STEP 2: Configure OpenRouter API Key

`config/config.yaml` file এ OpenRouter API key আছে:
```yaml
openrouter:
  api_key: "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"
```

**আপনার API key টি সঠিক আছে?** ✅

## 📋 STEP 3: Configure Exchange Credentials

`config/config.yaml` এ exchange credentials:
```yaml
exchange:
  api_key: "${BYBIT_API_KEY}"
  api_secret: "${BYBIT_API_SECRET}"
```

**Environment variable বা .env file এ set করুন:**
- `BYBIT_API_KEY=your_key`
- `BYBIT_API_SECRET=your_secret`

## 📋 STEP 4: Test Import

এখন test করি import ঠিক আছে কিনা:

```bash
cd "C:\Users\Administrator\Desktop\SADUN TRADING\trading_bot"
python ai_trading_system\main.py
```

**Output দেখুন এবং বলুন কি error পাচ্ছেন (যদি থাকে)।**

## 📋 STEP 5: Run the Bot

`.bat` file দিয়ে run করুন:
```bash
cd "C:\Users\Administrator\Desktop\SADUN TRADING\trading_bot\ai_trading_system"
run_ai_bot.bat
```

---

## 🎯 Next Steps (আমি আপনার output দেখে next step বলব):

1. ✅ Dependencies install - DONE
2. ⏳ Test import - আপনি test করুন
3. ⏳ Fix any errors - আমি fix করব
4. ⏳ Configure properly - আমি guide করব
5. ⏳ Run bot - Final step

