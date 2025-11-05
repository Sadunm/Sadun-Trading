"""
Mean Reversion Strategy with Z-Score and Bollinger Bands
"""
import numpy as np
from typing import Dict, Any, Optional
from .base_strategy import BaseStrategy
from ..features.indicators import IndicatorCalculator
from ..utils.logger import setup_logger

logger = setup_logger("mean_reversion_strategy")


class MeanReversionStrategy(BaseStrategy):
    """Mean reversion strategy using z-score and Bollinger Bands"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.timeframe = config.get('timeframe', '5m')
        self.z_score_threshold = config.get('z_score_threshold', 2.0)
        
    def generate_signal(
        self,
        symbol: str,
        features: Dict[str, Any],
        current_price: float,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Generate mean reversion signal"""
        if not self.enabled:
            return None
        
        try:
            # Get indicators
            zscore = features.get('zscore', [])
            bb_upper = features.get('bb_upper', [])
            bb_lower = features.get('bb_lower', [])
            bb_middle = features.get('bb_middle', [])
            bb_position = features.get('bb_position', [])
            rsi = features.get('rsi', [])
            
            if not all([zscore, bb_upper, bb_lower, bb_middle]):
                logger.warning(f"[WARN] Insufficient indicators for mean reversion")
                return None
            
            zscore_val = zscore[-1]
            bb_upper_val = bb_upper[-1]
            bb_lower_val = bb_lower[-1]
            bb_middle_val = bb_middle[-1]
            bb_pos = bb_position[-1] if bb_position else 0.5
            rsi_val = rsi[-1] if rsi else 50.0
            
            # Entry conditions
            action = 'FLAT'
            confidence = 0.0
            reason = ""
            
            # Long signal: oversold (z-score < -threshold, price near lower BB)
            if zscore_val < -self.z_score_threshold and bb_pos < 0.2:
                if rsi_val < 40:  # Additional confirmation
                    action = 'LONG'
                    confidence = min(0.9, 0.5 + abs(zscore_val) / self.z_score_threshold * 0.3)
                    reason = f"Oversold (z-score: {zscore_val:.2f}, BB position: {bb_pos:.2%})"
            
            # Short signal: overbought (z-score > threshold, price near upper BB)
            elif zscore_val > self.z_score_threshold and bb_pos > 0.8:
                if rsi_val > 60:  # Additional confirmation
                    action = 'SHORT'
                    confidence = min(0.9, 0.5 + abs(zscore_val) / self.z_score_threshold * 0.3)
                    reason = f"Overbought (z-score: {zscore_val:.2f}, BB position: {bb_pos:.2%})"
            
            if action == 'FLAT' or confidence < self.min_confidence:
                return None
            
            # Calculate stop loss and take profit
            # Mean reversion: target is mean (BB middle)
            bb_width = (bb_upper_val - bb_lower_val) / bb_middle_val * 100
            
            if action == 'LONG':
                # Entry near lower BB, target middle BB
                target_price = bb_middle_val
                stop_loss_pct = bb_width * 0.5  # Stop below lower BB
                take_profit_pct = abs((target_price - current_price) / current_price * 100)
            else:  # SHORT
                # Entry near upper BB, target middle BB
                target_price = bb_middle_val
                stop_loss_pct = bb_width * 0.5  # Stop above upper BB
                take_profit_pct = abs((current_price - target_price) / current_price * 100)
            
            stop_loss = current_price * (1 - stop_loss_pct / 100) if action == 'LONG' else current_price * (1 + stop_loss_pct / 100)
            take_profit = target_price
            
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
                'reason': reason
            }
            
        except Exception as e:
            logger.error(f"[ERROR] Error generating mean reversion signal: {e}")
            return None

