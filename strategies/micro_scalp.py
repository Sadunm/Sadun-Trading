"""
STRATEGY-1: Micro-Scalp Profit System
Goal: 0.25% net profit per trade (after fees), quick closes, compound growth
Capital: $10 (strict entry, precision over frequency)
"""
from typing import Dict, Any, Optional
from strategies.base_strategy import BaseStrategy
from utils.logger import setup_logger
from utils.validators import safe_divide

logger = setup_logger("micro_scalp")


class MicroScalpStrategy(BaseStrategy):
    """
    Micro-Scalp Strategy for $10 capital
    - Strict entry rules (precision over frequency)
    - 0.25% net profit target (after fees)
    - Fast exits with trailing stop
    - Maximum 3 positions ($2 each)
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        # Override base config for micro-scalp (values from config.yaml)
        self.max_hold_time_minutes = config.get('max_hold_time_minutes', 30)  # 30 min timeout
        self.stop_loss_pct = config.get('stop_loss_pct', 0.20)  # -0.20% stop loss (was 0.15%, increased to prevent instant hits)
        self.take_profit_pct = config.get('take_profit_pct', 0.50)  # +0.50% target (was 0.45%, increased for better risk/reward)
        
        # Entry filters (RELAXED for testnet/low volume markets)
        self.min_volatility_pct = 0.10  # Volatility > 0.10% (5m) - relaxed from 0.15%
        self.rsi_min = 30  # RSI between 30-60 (neutral zone) - expanded from 35-55
        self.rsi_max = 60
        self.volume_spike_ratio = 0.8  # Volume ≥ 0.8x average - relaxed from 1.2x (testnet has low volume)
        self.max_spread_pct = 0.05  # Spread < 0.05% - relaxed from 0.03%
        
        # Exit enhancements
        self.trailing_start_pct = 0.3  # Start trailing when profit > +0.3%
        self.trailing_stop_pct = 0.1  # Trailing stop at 0.1%
        self.volume_drop_threshold = 0.4  # Auto-close if volume drops > 40%
        
        logger.info(f"[MICRO-SCALP] Initialized - Target: {self.take_profit_pct}%, SL: {self.stop_loss_pct}%, Timeout: {self.max_hold_time_minutes}min")
    
    def generate_signal(
        self,
        symbol: str,
        indicators: Dict[str, Any],
        price: float,
        market_regime: str
    ) -> Optional[Dict[str, Any]]:
        """
        Generate signal with STRICT entry rules
        Only signals when ALL conditions match (precision over frequency)
        """
        try:
            # Required indicators
            rsi = indicators.get('rsi', 50.0)
            ema_5 = indicators.get('ema_5', None)
            ema_10 = indicators.get('ema_10', None)
            volume_ratio = indicators.get('volume_ratio', 1.0)
            atr_pct = indicators.get('atr_pct', 0.0)
            spread = indicators.get('spread', 0.0)
            
            # Validate all indicators present
            if ema_5 is None or ema_10 is None:
                return None
            
            # STRICT FILTER 1: Volatility check (> 0.15%)
            if atr_pct < self.min_volatility_pct:
                # Log occasionally to avoid spam
                if not hasattr(self, '_filter_log_count'):
                    self._filter_log_count = {}
                count = self._filter_log_count.get(f"{symbol}_atr", 0)
                self._filter_log_count[f"{symbol}_atr"] = count + 1
                if count % 50 == 0:
                    logger.info(f"[FILTER] {symbol} MICRO-SCALP: ATR={atr_pct:.2f}% < {self.min_volatility_pct:.2f}% threshold")
                return None  # Skip - not volatile enough
            
            # STRICT FILTER 2: RSI in neutral zone (35-55)
            if rsi < self.rsi_min or rsi > self.rsi_max:
                if not hasattr(self, '_filter_log_count'):
                    self._filter_log_count = {}
                count = self._filter_log_count.get(f"{symbol}_rsi", 0)
                self._filter_log_count[f"{symbol}_rsi"] = count + 1
                if count % 50 == 0:
                    logger.info(f"[FILTER] {symbol} MICRO-SCALP: RSI={rsi:.1f} not in [{self.rsi_min}-{self.rsi_max}] zone")
                return None  # Skip - RSI outside neutral zone
            
            # STRICT FILTER 3: EMA crossover or EMA5 > EMA10
            ema_crossover = False
            if ema_5 > ema_10:
                ema_crossover = True
            else:
                # Check if crossover just happened (within last 2 bars)
                ema_5_prev = indicators.get('ema_5_prev', ema_5)
                ema_10_prev = indicators.get('ema_10_prev', ema_10)
                if ema_5_prev <= ema_10_prev and ema_5 > ema_10:
                    ema_crossover = True
            
            if not ema_crossover:
                if not hasattr(self, '_filter_log_count'):
                    self._filter_log_count = {}
                count = self._filter_log_count.get(f"{symbol}_ema", 0)
                self._filter_log_count[f"{symbol}_ema"] = count + 1
                if count % 50 == 0:
                    logger.info(f"[FILTER] {symbol} MICRO-SCALP: EMA5={ema_5:.2f} <= EMA10={ema_10:.2f} (no crossover)")
                return None  # Skip - no EMA confirmation
            
            # STRICT FILTER 4: Volume spike (≥ 1.2x average)
            if volume_ratio < self.volume_spike_ratio:
                if not hasattr(self, '_filter_log_count'):
                    self._filter_log_count = {}
                count = self._filter_log_count.get(f"{symbol}_vol", 0)
                self._filter_log_count[f"{symbol}_vol"] = count + 1
                if count % 50 == 0:
                    logger.info(f"[FILTER] {symbol} MICRO-SCALP: Volume={volume_ratio:.2f}x < {self.volume_spike_ratio:.1f}x threshold")
                return None  # Skip - insufficient volume
            
            # STRICT FILTER 5: Spread check (< 0.03%)
            if spread >= self.max_spread_pct:
                if not hasattr(self, '_filter_log_count'):
                    self._filter_log_count = {}
                count = self._filter_log_count.get(f"{symbol}_spread", 0)
                self._filter_log_count[f"{symbol}_spread"] = count + 1
                if count % 50 == 0:
                    logger.info(f"[FILTER] {symbol} MICRO-SCALP: Spread={spread:.3f}% >= {self.max_spread_pct}% (low liquidity)")
                return None  # Skip - spread too high (low liquidity)
            
            # ALL FILTERS PASSED - Generate BUY signal
            # Calculate confidence based on how strong each condition is
            confidence = self._calculate_confidence(indicators, rsi, volume_ratio, atr_pct)
            
            if confidence >= self.confidence_threshold:
                logger.info(
                    f"[MICRO-SCALP] {symbol} BUY: "
                    f"RSI={rsi:.1f} (35-55✓), "
                    f"EMA5={ema_5:.2f}>EMA10={ema_10:.2f}✓, "
                    f"Vol={volume_ratio:.2f}x✓, "
                    f"ATR={atr_pct:.2f}%✓, "
                    f"Spread={spread:.3f}%✓, "
                    f"Conf={confidence:.1f}%"
                )
                return {
                    'action': 'BUY',
                    'confidence': confidence,
                    'reason': 'Micro-Scalp Strict Entry: All Filters Passed'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"[ERROR] Error generating micro-scalp signal: {e}")
            return None
    
    def _calculate_confidence(
        self,
        indicators: Dict[str, Any],
        rsi: float,
        volume_ratio: float,
        atr_pct: float
    ) -> float:
        """Calculate confidence score for entry"""
        base_confidence = 20.0
        
        # RSI bonus (closer to 50 = more neutral, better)
        rsi_center = 50.0
        rsi_distance = abs(rsi - rsi_center)
        rsi_bonus = max(0, 10 - rsi_distance)  # Max +10 if RSI = 50
        
        # Volume bonus (higher volume = better)
        volume_bonus = min(10, (volume_ratio - 1.2) * 10)  # Max +10
        
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
        - +0.45% target (covers fees + profit)
        - -0.15% stop loss
        - 30min timeout
        - Volume drop > 40%
        - Dynamic trailing when profit > +0.3%
        """
        try:
            if position.action == 'BUY':
                # Calculate current profit %
                price_change = ((current_price - position.entry_price) / position.entry_price) * 100.0
            else:  # SELL (short)
                price_change = ((position.entry_price - current_price) / position.entry_price) * 100.0
            
            # Exit reason
            exit_reason = None
            
            # CHECK 1: Take profit reached (+0.45%)
            if price_change >= self.take_profit_pct:
                exit_reason = 'TAKE_PROFIT'
            
            # CHECK 2: Stop loss hit (-0.15%)
            elif price_change <= -self.stop_loss_pct:
                exit_reason = 'STOP_LOSS'
            
            # CHECK 3: Timeout (30 min)
            else:
                from datetime import datetime
                hold_time = (datetime.now() - position.entry_time).total_seconds() / 60
                if hold_time >= self.max_hold_time_minutes:
                    exit_reason = 'TIMEOUT'
            
            # CHECK 4: Volume drop > 40%
            if not exit_reason:
                volume_ratio = indicators.get('volume_ratio', 1.0)
                entry_volume_ratio = getattr(position, 'entry_volume_ratio', 1.0)
                if volume_ratio < (entry_volume_ratio * (1 - self.volume_drop_threshold)):
                    exit_reason = 'VOLUME_DROP'
            
            # CHECK 5: Dynamic trailing stop (when profit > +0.3%)
            if not exit_reason and price_change > self.trailing_start_pct:
                # Trailing stop: if price drops 0.1% from peak, exit
                peak_profit = getattr(position, 'peak_profit_pct', price_change)
                if price_change > peak_profit:
                    # Update peak
                    position.peak_profit_pct = price_change
                else:
                    # Check if dropped from peak by trailing amount
                    drop_from_peak = peak_profit - price_change
                    if drop_from_peak >= self.trailing_stop_pct:
                        exit_reason = 'TRAILING_STOP'
            
            if exit_reason:
                return {
                    'should_exit': True,
                    'reason': exit_reason,
                    'profit_pct': price_change
                }
            
            return None
            
        except Exception as e:
            logger.error(f"[ERROR] Error checking exit: {e}")
            return None

