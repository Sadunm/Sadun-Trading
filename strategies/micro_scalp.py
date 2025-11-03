"""
STRATEGY-1: Micro-Scalp Profit System
Goal: 1.10% net profit per trade (after fees), quick closes, compound growth
Capital: $10 (ULTRA-STRICT entry, only highest quality)
"""
from typing import Dict, Any, Optional
from strategies.base_strategy import BaseStrategy
from utils.logger import setup_logger
from utils.validators import safe_divide

logger = setup_logger("micro_scalp")


class MicroScalpStrategy(BaseStrategy):
    """
    Micro-Scalp Strategy for $10 capital
    - ULTRA-STRICT entry rules (only highest quality = prevent losses)
    - 1.10% net profit target (after fees)
    - Fast exits with trailing stop
    - Maximum 3 positions ($2 each)
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        # Override base config for micro-scalp (values from config.yaml)
        self.max_hold_time_minutes = config.get('max_hold_time_minutes', 15)  # 15 min timeout (reduced for faster exits)
        self.stop_loss_pct = config.get('stop_loss_pct', 0.70)  # -0.70% stop loss (INCREASED from 0.55% - actual losses were 0.50-0.59%)
        self.take_profit_pct = config.get('take_profit_pct', 1.20)  # +1.20% target (INCREASED from 1.10% to compensate)
        
        # Entry filters (BALANCED - quality trades but allow some opportunities)
        self.min_volatility_pct = 0.15  # BALANCED: Volatility > 0.15% (was 0.18% - too strict, reduced for testnet)
        self.rsi_min = 38  # BALANCED: RSI between 38-52 (was 40-50 - too narrow, widened for more opportunities)
        self.rsi_max = 52
        self.volume_spike_ratio = 1.2  # BALANCED: Volume ≥ 1.2x average (was 1.3x - too strict, reduced for testnet)
        self.max_spread_pct = 0.03  # BALANCED: Spread < 0.03% (was 0.025% - too tight, relaxed for testnet)
        
        # Exit enhancements (OPTIMIZED for safe profits - proven techniques)
        self.trailing_start_pct = 0.50  # Start trailing when profit > +0.50% (let winners run)
        self.trailing_stop_pct = 0.10  # Trailing stop at 0.10% (tight to protect profits)
        self.volume_drop_threshold = 0.35  # Auto-close if volume drops > 35% (faster exit = lower risk)
        
        logger.info(f"[MICRO-SCALP] Initialized - Target: {self.take_profit_pct}%, SL: {self.stop_loss_pct}%, Timeout: {self.max_hold_time_minutes}min")
        logger.info(f"[MICRO-SCALP] Entry Filters: Volatility>{self.min_volatility_pct}%, RSI {self.rsi_min}-{self.rsi_max}, Volume≥{self.volume_spike_ratio}x, Spread<{self.max_spread_pct}%")
    
    def generate_signal(
        self,
        symbol: str,
        indicators: Dict[str, Any],
        price: float,
        market_regime: str
    ) -> Optional[Dict[str, Any]]:
        """
        Generate micro-scalp signal (ULTRA-STRICT entry rules)
        """
        try:
            if not self.enabled:
                return None
            
            # Get indicators
            rsi = indicators.get('rsi', 50.0)
            volume_ratio = indicators.get('volume_ratio', 1.0)
            atr_pct = indicators.get('atr_pct', 0.0)
            spread_pct = indicators.get('spread', 0.0)
            
            # EMA crossover check
            ema_9 = indicators.get('ema_9', price)
            ema_21 = indicators.get('ema_21', price)
            ema_cross = ema_9 > ema_21  # Bullish crossover
            
            # FILTER 1: Volatility check (BALANCED - need moderate moves but not too strict)
            if atr_pct < self.min_volatility_pct:
                # Log filter failures (occasionally to avoid spam)
                if not hasattr(self, '_filter_log_count'):
                    self._filter_log_count = {}
                count = self._filter_log_count.get(f"{symbol}_vol", 0)
                self._filter_log_count[f"{symbol}_vol"] = count + 1
                if count % 50 == 0:
                    logger.info(f"[FILTER] {symbol} MICRO-SCALP: ATR={atr_pct:.3f}% < {self.min_volatility_pct:.2f}% threshold")
                return None
            
            # FILTER 2: RSI check (BALANCED - wider range for more opportunities)
            if rsi < self.rsi_min or rsi > self.rsi_max:
                if not hasattr(self, '_filter_log_count'):
                    self._filter_log_count = {}
                count = self._filter_log_count.get(f"{symbol}_rsi", 0)
                self._filter_log_count[f"{symbol}_rsi"] = count + 1
                if count % 50 == 0:
                    logger.info(f"[FILTER] {symbol} MICRO-SCALP: RSI={rsi:.1f} not in [{self.rsi_min}-{self.rsi_max}] zone")
                return None
            
            # FILTER 3: Volume check (BALANCED - need momentum but not extreme)
            if volume_ratio < self.volume_spike_ratio:
                if not hasattr(self, '_filter_log_count'):
                    self._filter_log_count = {}
                count = self._filter_log_count.get(f"{symbol}_vol", 0)
                self._filter_log_count[f"{symbol}_vol"] = count + 1
                if count % 50 == 0:
                    logger.info(f"[FILTER] {symbol} MICRO-SCALP: Volume={volume_ratio:.2f}x < {self.volume_spike_ratio:.1f}x threshold")
                return None
            
            # FILTER 4: Spread check (BALANCED - reasonable costs)
            if spread_pct > self.max_spread_pct:
                if not hasattr(self, '_filter_log_count'):
                    self._filter_log_count = {}
                count = self._filter_log_count.get(f"{symbol}_spread", 0)
                self._filter_log_count[f"{symbol}_spread"] = count + 1
                if count % 50 == 0:
                    logger.info(f"[FILTER] {symbol} MICRO-SCALP: Spread={spread_pct:.3f}% > {self.max_spread_pct:.3f}% threshold")
                return None
            
            # FILTER 5: EMA crossover (must be bullish)
            if not ema_cross:
                if not hasattr(self, '_filter_log_count'):
                    self._filter_log_count = {}
                count = self._filter_log_count.get(f"{symbol}_ema", 0)
                self._filter_log_count[f"{symbol}_ema"] = count + 1
                if count % 50 == 0:
                    logger.info(f"[FILTER] {symbol} MICRO-SCALP: EMA crossover not bullish (EMA9={ema_9:.2f}, EMA21={ema_21:.2f})")
                return None
            
            # Calculate confidence
            confidence = self._calculate_confidence(indicators, rsi, volume_ratio, atr_pct)
            
            # Only take high confidence signals
            if confidence < self.confidence_threshold:
                if not hasattr(self, '_filter_log_count'):
                    self._filter_log_count = {}
                count = self._filter_log_count.get(f"{symbol}_conf", 0)
                self._filter_log_count[f"{symbol}_conf"] = count + 1
                if count % 20 == 0:  # Log confidence failures more often (every 20th)
                    logger.info(f"[FILTER] {symbol} MICRO-SCALP: Confidence={confidence:.1f}% < {self.confidence_threshold:.1f}% threshold")
                return None
            
            # Determine action
            action = 'BUY'  # Micro-scalp only does BUY (simpler)
            
            return {
                'action': action,
                'confidence': confidence,
                'reason': 'MICRO_SCALP'
            }
            
        except Exception as e:
            logger.error(f"[ERROR] Error generating micro-scalp signal for {symbol}: {e}", exc_info=True)
            return None
    
    def _calculate_confidence(
        self,
        indicators: Dict[str, Any],
        rsi: float,
        volume_ratio: float,
        atr_pct: float
    ) -> float:
        """
        Calculate confidence score (0-100)
        """
        base_confidence = 20.0
        
        # RSI bonus (closer to 50 = more neutral, better)
        rsi_center = 50.0
        rsi_distance = abs(rsi - rsi_center)
        rsi_bonus = max(0, 10 - rsi_distance)  # Max +10 if RSI = 50
        
        # Volume bonus (higher volume = better) - optimized for new 1.3x threshold
        volume_bonus = min(10, (volume_ratio - 1.3) * 10)  # Max +10 (base is now 1.3x)
        
        # Volatility bonus (moderate volatility is good)
        volatility_bonus = min(5, max(0, (atr_pct - 0.15) * 20))  # Max +5
        
        confidence = base_confidence + rsi_bonus + volume_bonus + volatility_bonus
        return min(100.0, confidence)
    
    def should_exit(
        self,
        position: Any,  # Position object
        current_price: float,
        indicators: Dict[str, Any],
        current_time: Any  # datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Enhanced exit logic:
        - +1.10% target (covers fees + profit)
        - -0.55% stop loss
        - 20min timeout
        - Volume drop > 35%
        - Dynamic trailing when profit > +0.50%
        """
        try:
            if position.action == 'BUY':
                # Calculate current profit %
                price_change = ((current_price - position.entry_price) / position.entry_price) * 100.0
            else:  # SELL (short)
                price_change = ((position.entry_price - current_price) / position.entry_price) * 100.0
            
            # Exit reason
            exit_reason = None
            
            # CHECK 1: Take profit reached (+1.10%)
            if price_change >= self.take_profit_pct:
                exit_reason = 'TAKE_PROFIT'
            
            # CHECK 2: Stop loss hit (-0.55%)
            elif price_change <= -self.stop_loss_pct:
                exit_reason = 'STOP_LOSS'
            
            # CHECK 3: Timeout (20 min)
            else:
                from datetime import datetime
                hold_time = (datetime.now() - position.entry_time).total_seconds() / 60
                if hold_time >= self.max_hold_time_minutes:
                    exit_reason = 'TIMEOUT'
            
            # CHECK 4: Volume drop > 35%
            if not exit_reason:
                volume_ratio = indicators.get('volume_ratio', 1.0)
                entry_volume_ratio = getattr(position, 'entry_volume_ratio', 1.0)
                if volume_ratio < (entry_volume_ratio * (1 - self.volume_drop_threshold)):
                    exit_reason = 'VOLUME_DROP'
            
            # CHECK 5: Dynamic trailing stop (when profit > +0.50%)
            if not exit_reason and price_change > self.trailing_start_pct:
                # Calculate highest profit reached (from position metadata if available)
                highest_profit = getattr(position, 'highest_profit_pct', price_change)
                if price_change > highest_profit:
                    highest_profit = price_change
                    position.highest_profit_pct = highest_profit  # Store for next check
                
                # Check if profit dropped from peak by trailing stop amount
                profit_drop = highest_profit - price_change
                if profit_drop >= self.trailing_stop_pct:
                    exit_reason = 'TRAILING_STOP'
            
            if exit_reason:
                return {
                    'should_exit': True,
                    'reason': exit_reason,
                    'current_profit_pct': price_change
                }
            
            return None
            
        except Exception as e:
            logger.error(f"[ERROR] Error in should_exit for {position.symbol}: {e}", exc_info=True)
            return None
