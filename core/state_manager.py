"""
Persistent state management
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from threading import Lock
from utils.logger import setup_logger

logger = setup_logger("state_manager")


class StateManager:
    """Persist and restore bot state"""
    
    def __init__(self, state_file: str = "data/bot_state.json"):
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()
        self.state = self._load_state()
    
    def _load_state(self) -> Dict[str, Any]:
        """Load state from JSON file"""
        try:
            if not self.state_file.exists():
                return self._default_state()
            
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
                logger.info("[OK] State loaded from file")
                return state
                
        except Exception as e:
            logger.error(f"[ERROR] Error loading state: {e}")
            return self._default_state()
    
    def _default_state(self) -> Dict[str, Any]:
        """Return default empty state"""
        return {
            'last_scan_time': None,
            'daily_trade_count': 0,
            'last_trade_date': None,
            'daily_pnl': 0.0,
            'last_update': None
        }
    
    def save_state(self):
        """Save current state to file"""
        try:
            with self.lock:
                with open(self.state_file, 'w', encoding='utf-8') as f:
                    json.dump(self.state, f, indent=2)
                logger.debug("[OK] State saved to file")
        except Exception as e:
            logger.error(f"[ERROR] Error saving state: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get state value"""
        with self.lock:
            return self.state.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set state value"""
        with self.lock:
            self.state[key] = value
            self.save_state()
    
    def increment_daily_trade_count(self):
        """Increment daily trade counter"""
        with self.lock:
            self.state['daily_trade_count'] = self.state.get('daily_trade_count', 0) + 1
            self.save_state()
    
    def reset_daily_counters(self):
        """Reset daily counters (call at start of new day)"""
        with self.lock:
            self.state['daily_trade_count'] = 0
            self.state['daily_pnl'] = 0.0
            self.state['last_trade_date'] = None
            self.save_state()
    
    def update_daily_pnl(self, pnl: float):
        """Update daily P&L"""
        with self.lock:
            current_pnl = self.state.get('daily_pnl', 0.0)
            self.state['daily_pnl'] = current_pnl + pnl
            self.save_state()

