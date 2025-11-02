"""
Safety mechanisms for Micro-Scalp Strategy
- Kill-switch (3 consecutive losses → pause 1 hour)
- Ping test (API latency check)
- Fee guard (profit margin validation)
- Balance safeguard
"""
import time
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, Tuple, Optional
from utils.logger import setup_logger

logger = setup_logger("safety_manager")


class SafetyManager:
    """Safety mechanisms for trading bot"""
    
    def __init__(self, config: Dict[str, Any]):
        self.lock = Lock()
        
        # Kill-switch
        self.consecutive_losses = 0
        self.kill_switch_threshold = 3  # 3 consecutive losses
        self.kill_switch_pause_hours = 1  # Pause 1 hour
        self.kill_switch_until = None  # datetime when kill-switch expires
        
        # Ping test
        self.max_latency_ms = 100  # Skip if latency > 100ms
        
        # Fee guard
        self.min_profit_margin_pct = 0.25  # Must have 0.25% profit margin
        
        # Balance safeguard
        self.max_positions = 3  # Max 3 positions
        self.max_position_size_usd = 2.0  # $2 per position (for $10 capital)
        
        # Min trade size
        self.min_notional_usd = 1.0  # Skip if minNotional > $1
        
        logger.info(f"[SAFETY] Initialized - Max positions: {self.max_positions}, Max size: ${self.max_position_size_usd}")
    
    def check_kill_switch(self) -> Tuple[bool, Optional[str]]:
        """
        Check if kill-switch is active
        Returns: (can_trade, reason)
        """
        with self.lock:
            if self.kill_switch_until:
                if datetime.now() < self.kill_switch_until:
                    remaining = (self.kill_switch_until - datetime.now()).total_seconds() / 60
                    return False, f"Kill-switch active - {remaining:.1f} minutes remaining"
                else:
                    # Kill-switch expired
                    self.kill_switch_until = None
                    self.consecutive_losses = 0
                    logger.info("[SAFETY] Kill-switch expired - trading resumed")
            
            return True, None
    
    def record_trade_result(self, pnl: float):
        """Record trade result for kill-switch tracking"""
        with self.lock:
            if pnl < 0:
                self.consecutive_losses += 1
                logger.warning(f"[SAFETY] Consecutive losses: {self.consecutive_losses}/{self.kill_switch_threshold}")
                
                if self.consecutive_losses >= self.kill_switch_threshold:
                    # Activate kill-switch
                    self.kill_switch_until = datetime.now() + timedelta(hours=self.kill_switch_pause_hours)
                    logger.error(
                        f"[KILL-SWITCH] ACTIVATED! "
                        f"{self.consecutive_losses} consecutive losses. "
                        f"Pausing for {self.kill_switch_pause_hours} hour(s). "
                        f"Resume at: {self.kill_switch_until}"
                    )
            else:
                # Reset on win
                self.consecutive_losses = 0
                logger.debug(f"[SAFETY] Win recorded - consecutive losses reset")
    
    def check_fee_guard(
        self,
        entry_price: float,
        target_profit_pct: float,
        expected_fees_pct: float
    ) -> Tuple[bool, str]:
        """
        Check if profit margin is sufficient after fees
        Returns: (is_valid, reason)
        """
        net_profit_pct = target_profit_pct - expected_fees_pct
        
        if net_profit_pct < self.min_profit_margin_pct:
            return False, f"Profit margin {net_profit_pct:.2f}% < minimum {self.min_profit_margin_pct:.2f}%"
        
        return True, "OK"
    
    def check_min_trade_size(self, min_notional: float) -> Tuple[bool, str]:
        """
        Check if coin meets minimum trade size requirement
        Returns: (is_valid, reason)
        """
        if min_notional > self.min_notional_usd:
            return False, f"Min notional ${min_notional:.2f} > limit ${self.min_notional_usd:.2f}"
        
        return True, "OK"
    
    def check_position_limit(self, current_positions: int) -> Tuple[bool, str]:
        """
        Check if position limit is reached
        Returns: (can_open, reason)
        """
        if current_positions >= self.max_positions:
            return False, f"Position limit reached ({current_positions}/{self.max_positions})"
        
        return True, "OK"
    
    def check_position_size(self, position_size_usd: float) -> Tuple[bool, str]:
        """
        Check if position size is within limit
        Returns: (is_valid, reason)
        """
        if position_size_usd > self.max_position_size_usd:
            return False, f"Position size ${position_size_usd:.2f} > limit ${self.max_position_size_usd:.2f}"
        
        return True, "OK"

