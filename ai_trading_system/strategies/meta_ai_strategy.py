"""
Meta AI Strategy - LLM Risk Filter
This strategy does NOT generate signals, only filters and validates other strategies
"""
from typing import Dict, Any, Optional, List
from strategies.base_strategy import BaseStrategy
from utils.openrouter_client import OpenRouterClient
from utils.logger import setup_logger

logger = setup_logger("meta_ai_strategy")


class MetaAIStrategy(BaseStrategy):
    """
    Meta AI Strategy - Risk Filter Only
    This strategy validates signals from other strategies using LLM
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.risk_check_enabled = config.get('risk_check_enabled', True)
        self.news_check_enabled = config.get('news_check_enabled', True)
        self.anomaly_check_enabled = config.get('anomaly_check_enabled', True)
        
        # Initialize OpenRouter client
        try:
            # Load config from YAML
            import yaml
            import os
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')
            with open(config_path, 'r') as f:
                config_obj = yaml.safe_load(f)
            openrouter_config = config_obj.get('openrouter', {})
            api_key = openrouter_config.get('api_key')
            
            if api_key:
                self.ai_client = OpenRouterClient(
                    api_key=api_key,
                    base_url=openrouter_config.get('base_url', 'https://openrouter.ai/api/v1')
                )
            else:
                logger.warning("[WARN] OpenRouter API key not found, AI filtering disabled")
                self.ai_client = None
        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize AI client: {e}")
            self.ai_client = None
    
    def generate_signal(
        self,
        symbol: str,
        features: Dict[str, Any],
        current_price: float,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Meta AI Strategy does NOT generate signals
        This method should never be called directly
        """
        logger.warning("[WARN] Meta AI Strategy should not generate signals directly")
        return None
    
    def validate_signal(
        self,
        signal: Dict[str, Any],
        symbol: str,
        features: Dict[str, Any],
        current_price: float
    ) -> Dict[str, Any]:
        """
        Validate signal using AI risk checks
        
        Returns:
            {
                'approved': bool,
                'confidence': float,
                'warnings': List[str],
                'checks': Dict[str, Any]
            }
        """
        if not self.enabled or not self.ai_client:
            # If AI disabled, approve by default
            return {
                'approved': True,
                'confidence': 0.5,
                'warnings': [],
                'checks': {'ai_disabled': True}
            }
        
        try:
            warnings = []
            checks = {}
            
            # 1. Risk Review
            if self.risk_check_enabled:
                risk_review = self.ai_client.risk_review(
                    symbol=symbol,
                    strategy=signal.get('reason', 'unknown'),
                    action=signal.get('action', 'FLAT'),
                    entry_price=current_price,
                    confidence=signal.get('confidence', 0.0)
                )
                checks['risk_review'] = risk_review
                
                if not risk_review.get('approved', True):
                    warnings.append(f"Risk review rejected: {risk_review.get('reason', 'No reason')}")
            
            # 2. News Check
            if self.news_check_enabled:
                news_check = self.ai_client.check_news_risk(symbol)
                checks['news_check'] = news_check
                
                if news_check.get('high_risk', False):
                    warnings.append(f"News risk detected: {news_check.get('summary', 'High risk')}")
            
            # 3. Anomaly Detection
            if self.anomaly_check_enabled:
                prices = features.get('price', [])
                volumes = features.get('volume', [])
                
                if len(prices) >= 20 and len(volumes) >= 20:
                    anomaly = self.ai_client.detect_anomaly(
                        symbol=symbol,
                        price_data=prices[-20:],
                        volume_data=volumes[-20:]
                    )
                    checks['anomaly'] = anomaly
                    
                    if anomaly.get('anomaly_detected', False):
                        severity = anomaly.get('severity', 'low')
                        if severity in ['high', 'medium']:
                            warnings.append(f"Anomaly detected ({severity}): {anomaly.get('explanation', 'Unknown')}")
            
            # Decision
            approved = len(warnings) == 0
            
            # Calculate confidence based on checks
            confidence = signal.get('confidence', 0.0)
            if checks.get('risk_review'):
                ai_confidence = checks['risk_review'].get('confidence', 0.5)
                confidence = (confidence + ai_confidence) / 2  # Average
            
            return {
                'approved': approved,
                'confidence': confidence,
                'warnings': warnings,
                'checks': checks
            }
            
        except Exception as e:
            logger.error(f"[ERROR] Error in AI validation: {e}")
            # Fail-open: approve if AI check fails
            return {
                'approved': True,
                'confidence': signal.get('confidence', 0.0),
                'warnings': [f'AI validation error: {str(e)}'],
                'checks': {'error': str(e)}
            }

