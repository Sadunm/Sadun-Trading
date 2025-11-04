"""
Trend Following Strategy with TFT Forecasting
"""
import numpy as np
from typing import Dict, Any, Optional
from strategies.base_strategy import BaseStrategy
from models.tft_model import TFTModel
from features.indicators import IndicatorCalculator
from utils.logger import setup_logger

logger = setup_logger("trend_following_strategy")


class TrendFollowingStrategy(BaseStrategy):
    """Trend following strategy using TFT forecasting"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.timeframe = config.get('timeframe', '5m')
        self.forecast_horizons = config.get('forecast_horizons', [1, 4, 12, 24])
        
        # Initialize TFT model
        self.tft_model = TFTModel(
            sequence_length=60,
            forecast_horizon=max(self.forecast_horizons)
        )
        
    def generate_signal(
        self,
        symbol: str,
        features: Dict[str, Any],
        current_price: float,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Generate trend following signal"""
        if not self.enabled:
            return None
        
        try:
            # Get price sequence
            prices = features.get('price', [])
            
            if len(prices) < 60:
                logger.warning(f"[WARN] Insufficient data for trend following (need 60, got {len(prices)})")
                return None
            
            # Prepare sequence for TFT
            sequence = np.array(prices[-60:]).reshape(-1, 1)
            
            # Get forecast
            forecast, confidence = self.tft_model.forecast(sequence)
            
            # Get forecast slope and intensity
            slope = self.tft_model.get_forecast_slope(sequence)
            intensity = self.tft_model.get_forecast_intensity(sequence)
            
            # Determine action based on forecast
            action = 'FLAT'
            confidence_score = 0.0
            reason = ""
            
            # Strong upward trend
            if slope > 0.5 and intensity > 0.3:
                action = 'LONG'
                confidence_score = min(0.95, 0.6 + abs(slope) / 5.0 + intensity / 2.0)
                reason = f"Strong upward trend (slope: {slope:.2f}%, intensity: {intensity:.2f})"
            
            # Strong downward trend
            elif slope < -0.5 and intensity > 0.3:
                action = 'SHORT'
                confidence_score = min(0.95, 0.6 + abs(slope) / 5.0 + intensity / 2.0)
                reason = f"Strong downward trend (slope: {slope:.2f}%, intensity: {intensity:.2f})"
            
            # Moderate trend
            elif abs(slope) > 0.2 and intensity > 0.2:
                action = 'LONG' if slope > 0 else 'SHORT'
                confidence_score = min(0.85, 0.5 + abs(slope) / 3.0 + intensity / 3.0)
                reason = f"Moderate trend (slope: {slope:.2f}%, intensity: {intensity:.2f})"
            
            if action == 'FLAT' or confidence_score < self.min_confidence:
                return None
            
            # Calculate stop loss and take profit based on forecast
            forecast_price = forecast[-1]  # Final forecast price
            
            # Get ATR for stop loss
            atr_pct = features.get('atr_pct', [])
            current_atr_pct = atr_pct[-1] if atr_pct else 0.5
            
            if action == 'LONG':
                # Target: forecast price
                take_profit = forecast_price
                # Stop: 2x ATR below entry
                stop_loss = current_price * (1 - current_atr_pct * 2 / 100)
            else:  # SHORT
                # Target: forecast price
                take_profit = forecast_price
                # Stop: 2x ATR above entry
                stop_loss = current_price * (1 + current_atr_pct * 2 / 100)
            
            # Expected return and risk
            expected_return = abs((take_profit - current_price) / current_price * 100)
            expected_risk = abs((stop_loss - current_price) / current_price * 100)
            
            return {
                'action': action,
                'confidence': confidence_score,
                'entry_price': current_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'expected_return': expected_return,
                'expected_risk': expected_risk,
                'reason': reason,
                'forecast_slope': slope,
                'forecast_intensity': intensity
            }
            
        except Exception as e:
            logger.error(f"[ERROR] Error generating trend following signal: {e}")
            return None

