"""
LightGBM Model for Trading Signals
"""
import lightgbm as lgb
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
import pickle
import os
from datetime import datetime
from ..utils.logger import setup_logger

logger = setup_logger("lightgbm_model")


class LightGBMModel:
    """LightGBM model for trading signal prediction"""
    
    def __init__(self, model_dir: str = "ai_trading_system/models/saved"):
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        self.model = None
        self.feature_importance_ = None
        
    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[List[str]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Train LightGBM model
        
        Args:
            X: Feature matrix (n_samples, n_features)
            y: Target labels (n_samples,) - 1 for long, -1 for short, 0 for flat
            feature_names: List of feature names
            params: LightGBM parameters
        """
        if len(X) == 0 or len(y) == 0:
            logger.error("[ERROR] Empty training data")
            return {'success': False, 'error': 'Empty data'}
        
        # Default parameters
        default_params = {
            'objective': 'multiclass',
            'num_class': 3,  # long, short, flat
            'metric': 'multi_logloss',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.9,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1,
            'seed': 42
        }
        
        if params:
            default_params.update(params)
        
        # Convert labels to 0, 1, 2 (flat, long, short)
        y_class = np.where(y == 0, 0, np.where(y > 0, 1, 2))
        
        # Create dataset
        train_data = lgb.Dataset(
            X,
            label=y_class,
            feature_name=feature_names
        )
        
        # Train
        try:
            self.model = lgb.train(
                default_params,
                train_data,
                num_boost_round=100,
                valid_sets=[train_data],
                callbacks=[lgb.log_evaluation(period=10)]
            )
            
            # Feature importance
            self.feature_importance_ = self.model.feature_importance(importance_type='gain')
            
            logger.info(f"[MODEL] LightGBM trained on {len(X)} samples")
            
            return {
                'success': True,
                'n_samples': len(X),
                'n_features': X.shape[1],
                'feature_importance': dict(zip(
                    feature_names or [f'feature_{i}' for i in range(X.shape[1])],
                    self.feature_importance_.tolist()
                )) if feature_names else None
            }
        except Exception as e:
            logger.error(f"[ERROR] Training failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict signals
        
        Returns:
            predictions: Predicted class (-1, 0, 1)
            probabilities: Prediction probabilities
        """
        if self.model is None:
            logger.error("[ERROR] Model not trained")
            return np.zeros(len(X)), np.zeros((len(X), 3))
        
        try:
            # Predict probabilities
            proba = self.model.predict(X)
            
            # Get predictions (class with highest probability)
            predictions = np.argmax(proba, axis=1)
            
            # Convert back to -1, 0, 1
            predictions = np.where(predictions == 0, 0, np.where(predictions == 1, 1, -1))
            
            return predictions, proba
            
        except Exception as e:
            logger.error(f"[ERROR] Prediction failed: {e}")
            return np.zeros(len(X)), np.zeros((len(X), 3))
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict probabilities"""
        _, proba = self.predict(X)
        return proba
    
    def save(self, filename: Optional[str] = None):
        """Save model"""
        if self.model is None:
            logger.warning("[WARN] No model to save")
            return
        
        if filename is None:
            filename = f"lightgbm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        
        filepath = os.path.join(self.model_dir, filename)
        
        try:
            with open(filepath, 'wb') as f:
                pickle.dump({
                    'model': self.model,
                    'feature_importance': self.feature_importance_,
                    'timestamp': datetime.now().isoformat()
                }, f)
            logger.info(f"[MODEL] Model saved to {filepath}")
        except Exception as e:
            logger.error(f"[ERROR] Failed to save model: {e}")
    
    def load(self, filename: str):
        """Load model"""
        filepath = os.path.join(self.model_dir, filename)
        
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
                self.model = data['model']
                self.feature_importance_ = data.get('feature_importance')
            logger.info(f"[MODEL] Model loaded from {filepath}")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Failed to load model: {e}")
            return False

