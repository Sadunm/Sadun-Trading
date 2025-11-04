"""
OpenRouter API Client for AI Risk Filtering
"""
import requests
import time
from typing import Dict, Any, Optional, List
from utils.logger import setup_logger

# Import path fix
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = setup_logger("openrouter_client")


class OpenRouterClient:
    """Client for OpenRouter API - LLM integration for risk filtering"""
    
    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.timeout = 30.0
        self.max_retries = 3
        
    def call_ai(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 500
    ) -> Optional[Dict[str, Any]]:
        """
        Call OpenRouter AI model
        
        Args:
            model: Model identifier (e.g., "deepseek/deepseek-chat")
            prompt: User prompt
            system_prompt: System prompt (optional)
            temperature: Temperature for generation (0.0-1.0)
            max_tokens: Maximum tokens to generate
        
        Returns:
            Response dict with 'content' and 'metadata', or None if error
        """
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Sadunm/Sadun-Trading",
            "X-Title": "Sadun Trading Bot"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                    
                    return {
                        'content': content,
                        'model': data.get('model'),
                        'usage': data.get('usage', {}),
                        'success': True
                    }
                else:
                    logger.warning(f"[WARN] OpenRouter API error: {response.status_code} - {response.text}")
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    return {'success': False, 'error': f"HTTP {response.status_code}"}
                    
            except requests.exceptions.Timeout:
                logger.warning(f"[WARN] OpenRouter API timeout (attempt {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return {'success': False, 'error': 'Timeout'}
                
            except Exception as e:
                logger.error(f"[ERROR] OpenRouter API error: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return {'success': False, 'error': str(e)}
        
        return {'success': False, 'error': 'Max retries exceeded'}
    
    def risk_review(
        self,
        symbol: str,
        strategy: str,
        action: str,
        entry_price: float,
        confidence: float,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        AI risk review for trade signal
        
        Returns:
            {
                'approved': bool,
                'confidence': float,
                'reason': str,
                'warnings': List[str]
            }
        """
        system_prompt = """You are a risk management AI for crypto trading. 
Your job is to review trade signals and identify potential risks.
You MUST NOT generate signals, only validate and filter existing ones.
Respond in JSON format: {"approved": true/false, "confidence": 0.0-1.0, "reason": "explanation", "warnings": ["warning1", "warning2"]}"""
        
        prompt = f"""Review this trade signal:
Symbol: {symbol}
Strategy: {strategy}
Action: {action}
Entry Price: ${entry_price:.2f}
Confidence: {confidence:.2%}

Check for:
1. Market volatility risks
2. Liquidity concerns
3. Technical indicator conflicts
4. Risk/reward ratio issues
5. Market regime compatibility

Respond with JSON only."""
        
        model = model or "deepseek/deepseek-chat"
        response = self.call_ai(model, prompt, system_prompt, temperature=0.2, max_tokens=300)
        
        if not response or not response.get('success'):
            # Default: approve if AI fails (fail-open for reliability)
            logger.warning(f"[WARN] AI risk review failed, defaulting to approved")
            return {
                'approved': True,
                'confidence': 0.5,
                'reason': 'AI review unavailable',
                'warnings': []
            }
        
        # Parse JSON response
        try:
            import json
            content = response['content'].strip()
            # Remove markdown code blocks if present
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
            content = content.strip()
            
            result = json.loads(content)
            return {
                'approved': result.get('approved', True),
                'confidence': float(result.get('confidence', 0.5)),
                'reason': result.get('reason', 'No reason provided'),
                'warnings': result.get('warnings', [])
            }
        except Exception as e:
            logger.error(f"[ERROR] Failed to parse AI response: {e}")
            logger.error(f"[ERROR] Response: {response.get('content', '')}")
            # Default: approve if parsing fails
            return {
                'approved': True,
                'confidence': 0.5,
                'reason': 'AI response parsing failed',
                'warnings': []
            }
    
    def check_news_risk(
        self,
        symbol: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check for news-related risks"""
        system_prompt = """You are a crypto news risk detector.
Identify if there are recent news events that could affect trading.
Respond with JSON: {"high_risk": true/false, "risk_level": "low/medium/high", "summary": "brief summary"}"""
        
        prompt = f"""Check for news risks for {symbol}:
1. Recent announcements
2. Exchange issues
3. Regulatory news
4. Major market events
5. Technical problems

Respond with JSON only."""
        
        model = model or "qwen/qwen-2.5-72b-instruct"
        response = self.call_ai(model, prompt, system_prompt, temperature=0.2, max_tokens=200)
        
        if not response or not response.get('success'):
            return {
                'high_risk': False,
                'risk_level': 'low',
                'summary': 'News check unavailable'
            }
        
        try:
            import json
            content = response['content'].strip()
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
            content = content.strip()
            
            result = json.loads(content)
            return {
                'high_risk': result.get('high_risk', False),
                'risk_level': result.get('risk_level', 'low'),
                'summary': result.get('summary', 'No summary')
            }
        except Exception as e:
            logger.error(f"[ERROR] Failed to parse news check: {e}")
            return {
                'high_risk': False,
                'risk_level': 'low',
                'summary': 'News check parsing failed'
            }
    
    def detect_anomaly(
        self,
        symbol: str,
        price_data: List[float],
        volume_data: List[float],
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Detect market anomalies"""
        system_prompt = """You are a market anomaly detector.
Analyze price and volume data for anomalies.
Respond with JSON: {"anomaly_detected": true/false, "anomaly_type": "type", "severity": "low/medium/high", "explanation": "brief"}"""
        
        # Prepare data summary
        price_changes = [abs(price_data[i] - price_data[i-1]) / price_data[i-1] * 100 
                        for i in range(1, len(price_data))] if len(price_data) > 1 else []
        avg_volume = sum(volume_data) / len(volume_data) if volume_data else 0
        
        prompt = f"""Analyze for anomalies in {symbol}:
Recent price changes: {price_changes[-10:] if price_changes else []}%
Average volume: {avg_volume:.2f}
Recent volumes: {volume_data[-10:] if len(volume_data) >= 10 else volume_data}

Check for:
1. Sudden price spikes/drops
2. Volume anomalies
3. Unusual volatility
4. Market manipulation signs

Respond with JSON only."""
        
        model = model or "meta-llama/llama-3.3-70b-instruct"
        response = self.call_ai(model, prompt, system_prompt, temperature=0.2, max_tokens=200)
        
        if not response or not response.get('success'):
            return {
                'anomaly_detected': False,
                'anomaly_type': 'none',
                'severity': 'low',
                'explanation': 'Anomaly check unavailable'
            }
        
        try:
            import json
            content = response['content'].strip()
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
            content = content.strip()
            
            result = json.loads(content)
            return {
                'anomaly_detected': result.get('anomaly_detected', False),
                'anomaly_type': result.get('anomaly_type', 'none'),
                'severity': result.get('severity', 'low'),
                'explanation': result.get('explanation', 'No explanation')
            }
        except Exception as e:
            logger.error(f"[ERROR] Failed to parse anomaly detection: {e}")
            return {
                'anomaly_detected': False,
                'anomaly_type': 'none',
                'severity': 'low',
                'explanation': 'Anomaly check parsing failed'
            }

