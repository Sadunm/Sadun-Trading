"""
Short-Term Momentum Strategy with LightGBM
"""
import numpy as np
from typing import Dict, Any, Optional
from strategies.base_strategy import BaseStrategy
from models.lightgbm_model import LightGBMModel
from features.indicators import IndicatorCalculator
from utils.logger import setup_logger

logger = setup_logger("momentum_strategy")


class MomentumStrategy(BaseStrategy):
    """ML-based momentum strategy using LightGBM"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.timeframe = config.get('timeframe', '5m')
        self.lookback_periods = config.get('lookback_periods', 20)
        
        # Initialize model
        self.model = LightGBMModel()
        self.model_loaded = False
        
        # Try to load pre-trained model
        # self.model.load('momentum_model.pkl')  # Uncomment if model exists
        
    def generate_signal(
        self,
        symbol: str,
        features: Dict[str, Any],
        current_price: float,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Generate momentum signal"""
        if not self.enabled:
            return None
        
        try:
            # Extract features
            if not features:
                logger.warning(f"[WARN] No features available for {symbol}")
                return None
            
            # Build feature vector
            feature_vector = self._build_feature_vector(features)
            
            if feature_vector is None:
                return None
            
            # Predict signal
            if self.model_loaded and self.model.model is not None:
                prediction, proba = self.model.predict(feature_vector.reshape(1, -1))
                action_idx = prediction[0]
                confidence = float(np.max(proba[0]))
                
                # Map prediction to action
                if action_idx == 1:
                    action = 'LONG'
                elif action_idx == -1:
                    action = 'SHORT'
                else:
                    action = 'FLAT'
            else:
                # Fallback: rule-based momentum
                action, confidence = self._rule_based_signal(features)
            
            if action == 'FLAT' or confidence < self.min_confidence:
                return None
            
            # Calculate stop loss and take profit
            atr = features.get('atr', [])
            atr_pct = features.get('atr_pct', [])
            
            if len(atr_pct) > 0:
                current_atr_pct = atr_pct[-1]
            else:
                current_atr_pct = 0.5  # Default 0.5%
            
            stop_loss_pct = current_atr_pct * 2.0  # 2x ATR
            take_profit_pct = current_atr_pct * 3.0  # 3x ATR
            
            if action == 'LONG':
                stop_loss = current_price * (1 - stop_loss_pct / 100)
                take_profit = current_price * (1 + take_profit_pct / 100)
            else:  # SHORT
                stop_loss = current_price * (1 + stop_loss_pct / 100)
                take_profit = current_price * (1 - take_profit_pct / 100)
            
            # Expected return and risk
            expected_return = take_profit_pct
            expected_risk = stop_loss_pct
            
            return {
                'action': action,
                'confidence': confidence,
                'entry_price': current_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'expected_return': expected_return,
                'expected_risk': expected_risk,
                'reason': f'Momentum signal (confidence: {confidence:.2%})'
            }
            
        except Exception as e:
            logger.error(f"[ERROR] Error generating momentum signal: {e}")
            return None
    
    def _build_feature_vector(self, features: Dict[str, Any]) -> Optional[np.ndarray]:
        """Build feature vector for model"""
        try:
            # Select key features
            feature_list = []
            
            # Returns
            for period in [1, 3, 5, 10, 20]:
                key = f'return_{period}'
                if key in features and len(features[key]) > 0:
                    feature_list.append(features[key][-1])
                else:
                    feature_list.append(0.0)
            
            # RSI
            if 'rsi' in features and len(features['rsi']) > 0:
                feature_list.append(features['rsi'][-1])
            else:
                feature_list.append(50.0)
            
            # MACD
            if 'macd_histogram' in features and len(features['macd_histogram']) > 0:
                feature_list.append(features['macd_histogram'][-1])
            else:
                feature_list.append(0.0)
            
            # Volume ratio
            if 'volume_ratio' in features and len(features['volume_ratio']) > 0:
                feature_list.append(features['volume_ratio'][-1])
            else:
                feature_list.append(1.0)
            
            # Volatility
            if 'volatility' in features and len(features['volatility']) > 0:
                feature_list.append(features['volatility'][-1])
            else:
                feature_list.append(0.0)
            
            # Momentum
            if 'momentum' in features and len(features['momentum']) > 0:
                feature_list.append(features['momentum'][-1])
            else:
                feature_list.append(0.0)
            
            return np.array(feature_list)
            
        except Exception as e:
            logger.error(f"[ERROR] Error building feature vector: {e}")
            return None
    
    def _rule_based_signal(self, features: Dict[str, Any]) -> tuple:
        """Fallback rule-based signal"""
        try:
            # Get latest values
            rsi = features.get('rsi', [])
            macd_hist = features.get('macd_histogram', [])
            momentum = features.get('momentum', [])
            volume_ratio = features.get('volume_ratio', [])
            
            if not all([rsi, macd_hist, momentum, volume_ratio]):
                return 'FLAT', 0.0
            
            rsi_val = rsi[-1]
            macd_val = macd_hist[-1]
            mom_val = momentum[-1]
            vol_val = volume_ratio[-1]
            
            # Long signal
            if (rsi_val < 50 and macd_val > 0 and mom_val > 0 and vol_val > 1.2):
                confidence = min(0.9, 0.5 + abs(mom_val) / 100 + (vol_val - 1.0) * 0.2)
                return 'LONG', confidence
            
            # Short signal
            elif (rsi_val > 50 and macd_val < 0 and mom_val < 0 and vol_val > 1.2):
                confidence = min(0.9, 0.5 + abs(mom_val) / 100 + (vol_val - 1.0) * 0.2)
                return 'SHORT', confidence
            
            return 'FLAT', 0.0
            
        except Exception as e:
            logger.error(f"[ERROR] Error in rule-based signal: {e}")
            return 'FLAT', 0.0

