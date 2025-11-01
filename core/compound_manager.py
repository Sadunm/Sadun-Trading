"""
Auto compounding manager - automatic profit reinvestment
"""
from datetime import datetime, date
from threading import Lock
from typing import Dict, Any
from utils.validators import validate_price
from utils.logger import setup_logger

logger = setup_logger("compound")


class CompoundManager:
    """Manage automatic profit compounding"""
    
    def __init__(self, config: Dict[str, Any]):
        self.enabled = config.get('auto_compounding', True)
        self.threshold_usd = config.get('compounding_threshold', 50.0)
        self.interval = config.get('compounding_interval', 'daily')  # 'immediate', 'daily', 'weekly'
        
        # Track accumulated profits
        self.accumulated_profits = 0.0
        self.last_compound_date = date.today()
        self.compound_count = 0
        self.total_compounded = 0.0
        
        self.lock = Lock()
        
        logger.info(f"[COMPOUND] Auto compounding: {'ENABLED' if self.enabled else 'DISABLED'}")
        if self.enabled:
            logger.info(f"[COMPOUND] Threshold: ${self.threshold_usd:.2f}, Interval: {self.interval}")
    
    def add_profit(self, profit_usd: float) -> float:
        """
        Add profit and check if should compound
        
        Args:
            profit_usd: Profit amount (can be negative)
        
        Returns:
            Amount compounded (if triggered), 0 otherwise
        """
        if not self.enabled:
            return 0.0
        
        # Only compound positive profits
        if not validate_price(profit_usd) or profit_usd <= 0:
            return 0.0
        
        with self.lock:
            self.accumulated_profits += profit_usd
            
            # Check if should compound
            should_compound = self._should_compound()
            
            if should_compound:
                return self._apply_compounding()
        
        return 0.0
    
    def _should_compound(self) -> bool:
        """Check if compounding conditions are met"""
        try:
            # Must meet threshold
            if self.accumulated_profits < self.threshold_usd:
                return False
            
            # Check interval
            today = date.today()
            
            if self.interval == 'immediate':
                # Compound immediately when threshold met
                return True
            
            elif self.interval == 'daily':
                # Compound once per day if threshold met
                if today > self.last_compound_date:
                    return True
            
            elif self.interval == 'weekly':
                # Compound once per week if threshold met
                days_since_last = (today - self.last_compound_date).days
                if days_since_last >= 7:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"[ERROR] Error checking compound conditions: {e}")
            return False
    
    def _apply_compounding(self) -> float:
        """Apply compounding to trading capital"""
        try:
            with self.lock:
                profit_to_compound = self.accumulated_profits
                
                # Reset accumulated
                self.accumulated_profits = 0.0
                self.last_compound_date = date.today()
                self.compound_count += 1
                self.total_compounded += profit_to_compound
            
            logger.info(f"[COMPOUND] Compounding ${profit_to_compound:.2f} profits")
            logger.info(f"[COMPOUND] Total compounded so far: ${self.total_compounded:.2f} (count: {self.compound_count})")
            
            # Return profit amount (bot will add to capital)
            return profit_to_compound
            
        except Exception as e:
            logger.error(f"[ERROR] Error applying compounding: {e}", exc_info=True)
            return 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get compounding statistics"""
        with self.lock:
            return {
                'enabled': self.enabled,
                'threshold': self.threshold_usd,
                'interval': self.interval,
                'accumulated_profits': self.accumulated_profits,
                'compound_count': self.compound_count,
                'total_compounded': self.total_compounded,
                'last_compound_date': self.last_compound_date.isoformat()
            }

