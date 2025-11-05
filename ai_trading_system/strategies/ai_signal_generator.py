"""
AI Signal Generator - Uses DeepSeek to generate trading signals from market data
This is the CORE AI component that actually generates signals
"""
import numpy as np
from typing import Dict, Any, Optional, List
from ..utils.openrouter_client import OpenRouterClient
from ..utils.logger import setup_logger
import json
import yaml
import os

logger = setup_logger("ai_signal_generator")


class AISignalGenerator:
    """
    AI-Powered Signal Generator
    Uses DeepSeek to analyze market data and generate trading signals
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize AI signal generator with OpenRouter/DeepSeek"""
        try:
            # Load config
            if not config_path:
                config_path = os.path.join(
                    os.path.dirname(__file__), '..', 'config', 'config.yaml'
                )
            
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            openrouter_config = config.get('openrouter', {})
            api_key = openrouter_config.get('api_key')
            
            if not api_key:
                raise ValueError("OpenRouter API key not found in config")
            
            self.ai_client = OpenRouterClient(
                api_key=api_key,
                base_url=openrouter_config.get('base_url', 'https://openrouter.ai/api/v1')
            )
            
            self.model = openrouter_config.get('default_model', 'deepseek/deepseek-chat')
            
            logger.info(f"[AI] Signal generator initialized with model: {self.model}")
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize AI signal generator: {e}")
            self.ai_client = None
            self.model = None
    
    def generate_signal(
        self,
        symbol: str,
        features: Dict[str, Any],
        current_price: float,
        ohlcv_data: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate trading signal using AI analysis
        
        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            features: Technical indicators dict
            current_price: Current market price
            ohlcv_data: List of OHLCV candles
        
        Returns:
            Signal dict with action, confidence, entry_price, stop_loss, take_profit
            or None if no signal
        """
        if not self.ai_client or not self.model:
            logger.warning("[WARN] AI client not available, cannot generate signals")
            return None
        
        try:
            # Prepare market summary for AI
            market_summary = self._prepare_market_summary(
                symbol=symbol,
                features=features,
                current_price=current_price,
                ohlcv_data=ohlcv_data
            )
            
            # AI prompt for signal generation
            system_prompt = """You are an expert crypto trading AI. Analyze market data and generate trading signals.
You MUST respond ONLY with valid JSON in this exact format:
{
    "action": "LONG" or "SHORT" or "FLAT",
    "confidence": 0.0 to 1.0,
    "entry_price": number,
    "stop_loss": number,
    "take_profit": number,
    "reason": "brief explanation",
    "expected_return_pct": number,
    "expected_risk_pct": number
}

Rules:
- Only generate LONG or SHORT if confidence > 0.6
- If confidence <= 0.6, set action to "FLAT"
- stop_loss and take_profit must be absolute prices
- expected_return_pct and expected_risk_pct are percentages
- reason must be clear and concise"""
            
            user_prompt = f"""Analyze this market data for {symbol}:

{market_summary}

Current Price: ${current_price:.2f}

Generate a trading signal based on:
1. Technical indicators (RSI, MACD, Bollinger Bands, ATR)
2. Price momentum and trend
3. Volume analysis
4. Volatility assessment
5. Risk/reward ratio

Respond with JSON only."""
            
            # Call AI
            response = self.ai_client.call_ai(
                model=self.model,
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.3,  # Lower temperature for more consistent signals
                max_tokens=500
            )
            
            if not response or not response.get('success'):
                logger.warning(f"[WARN] AI signal generation failed for {symbol}")
                return None
            
            # Parse AI response
            signal = self._parse_ai_response(response['content'], current_price)
            
            if signal and signal.get('action') != 'FLAT':
                logger.info(f"[AI-SIGNAL] {symbol}: {signal.get('action')} @ ${signal.get('entry_price', 0):.2f} "
                           f"(confidence: {signal.get('confidence', 0):.2%}, reason: {signal.get('reason', 'N/A')})")
            
            return signal
            
        except Exception as e:
            logger.error(f"[ERROR] Error generating AI signal for {symbol}: {e}", exc_info=True)
            return None
    
    def _prepare_market_summary(
        self,
        symbol: str,
        features: Dict[str, Any],
        current_price: float,
        ohlcv_data: List[Dict[str, Any]]
    ) -> str:
        """Prepare market data summary for AI analysis"""
        try:
            # Get latest indicator values
            rsi = features.get('rsi', [])
            macd_hist = features.get('macd_histogram', [])
            bb_upper = features.get('bb_upper', [])
            bb_lower = features.get('bb_lower', [])
            bb_middle = features.get('bb_middle', [])
            atr_pct = features.get('atr_pct', [])
            volume_ratio = features.get('volume_ratio', [])
            volatility = features.get('volatility', [])
            
            # Safe extraction
            def safe_get(arr, default=0.0):
                if arr and len(arr) > 0:
                    val = arr[-1]
                    return float(val) if isinstance(val, (int, float, np.generic)) else default
                return default
            
            # Price movement
            prices = [c['close'] for c in ohlcv_data[-20:]]
            price_change_1h = ((prices[-1] - prices[-12]) / prices[-12] * 100) if len(prices) >= 12 else 0.0
            price_change_4h = ((prices[-1] - prices[0]) / prices[0] * 100) if len(prices) > 0 else 0.0
            
            # Prepare summary
            summary = f"""Market Data Summary for {symbol}:

PRICE:
- Current: ${current_price:.2f}
- 1h Change: {price_change_1h:+.2f}%
- 4h Change: {price_change_4h:+.2f}%
- Recent High: ${max(prices):.2f}
- Recent Low: ${min(prices):.2f}

TECHNICAL INDICATORS:
- RSI: {safe_get(rsi, 50.0):.2f} (oversold<30, overbought>70)
- MACD Histogram: {safe_get(macd_hist, 0.0):.4f} (positive=bullish, negative=bearish)
- Bollinger Bands:
  * Upper: ${safe_get(bb_upper, current_price):.2f}
  * Middle: ${safe_get(bb_middle, current_price):.2f}
  * Lower: ${safe_get(bb_lower, current_price):.2f}
  * Current position: {((current_price - safe_get(bb_lower, current_price)) / (safe_get(bb_upper, current_price) - safe_get(bb_lower, current_price)) * 100) if (safe_get(bb_upper, current_price) - safe_get(bb_lower, current_price)) > 0 else 50:.1f}% (0%=lower, 100%=upper)

VOLATILITY & RISK:
- ATR %: {safe_get(atr_pct, 0.0):.2f}%
- Volatility: {safe_get(volatility, 0.0):.2f}%
- Volume Ratio: {safe_get(volume_ratio, 1.0):.2f}x (1.0=average, >1.2=high volume)

TREND ANALYSIS:
- Price Trend: {"Bullish" if price_change_4h > 0 else "Bearish" if price_change_4h < 0 else "Neutral"}
- Momentum: {"Strong Up" if safe_get(macd_hist) > 0.01 else "Strong Down" if safe_get(macd_hist) < -0.01 else "Neutral"}"""
            
            return summary
            
        except Exception as e:
            logger.error(f"[ERROR] Error preparing market summary: {e}")
            return f"Market data for {symbol} - Current price: ${current_price:.2f}"
    
    def _parse_ai_response(self, content: str, current_price: float) -> Optional[Dict[str, Any]]:
        """Parse AI response and extract signal"""
        try:
            # Clean content
            content = content.strip()
            
            # Remove markdown code blocks
            if content.startswith('```'):
                parts = content.split('```')
                if len(parts) >= 2:
                    content = parts[1]
                    if content.startswith('json'):
                        content = content[4:]
            
            content = content.strip()
            
            # Try to extract JSON
            try:
                signal = json.loads(content)
            except json.JSONDecodeError:
                # Try to find JSON in the response
                import re
                json_match = re.search(r'\{[^{}]*"action"[^{}]*\}', content, re.DOTALL)
                if json_match:
                    signal = json.loads(json_match.group())
                else:
                    logger.error(f"[ERROR] No valid JSON found in AI response: {content[:200]}")
                    return None
            
            # Validate and normalize signal
            action = signal.get('action', 'FLAT').upper()
            if action not in ['LONG', 'SHORT', 'FLAT']:
                action = 'FLAT'
            
            confidence = float(signal.get('confidence', 0.0))
            confidence = max(0.0, min(1.0, confidence))  # Clamp to 0-1
            
            # If confidence too low, force FLAT
            if confidence < 0.6:
                action = 'FLAT'
            
            # Get prices
            entry_price = float(signal.get('entry_price', current_price))
            stop_loss = float(signal.get('stop_loss', 0.0))
            take_profit = float(signal.get('take_profit', 0.0))
            
            # If prices not provided, calculate from percentages
            if stop_loss == 0 or take_profit == 0:
                expected_risk_pct = float(signal.get('expected_risk_pct', 0.5))
                expected_return_pct = float(signal.get('expected_return_pct', 1.0))
                
                if action == 'LONG':
                    stop_loss = entry_price * (1 - expected_risk_pct / 100)
                    take_profit = entry_price * (1 + expected_return_pct / 100)
                elif action == 'SHORT':
                    stop_loss = entry_price * (1 + expected_risk_pct / 100)
                    take_profit = entry_price * (1 - expected_return_pct / 100)
            
            return {
                'action': action,
                'confidence': confidence,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'expected_return': float(signal.get('expected_return_pct', 1.0)),
                'expected_risk': float(signal.get('expected_risk_pct', 0.5)),
                'reason': signal.get('reason', 'AI signal'),
                'source': 'ai_generator'
            }
            
        except Exception as e:
            logger.error(f"[ERROR] Error parsing AI response: {e}")
            logger.error(f"[ERROR] Response content: {content[:500]}")
            return None

