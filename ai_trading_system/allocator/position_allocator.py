"""
Position Allocator - Meta-Strategy for Combining Strategy Signals
"""
import numpy as np
from typing import Dict, Any, List, Optional
from ..utils.logger import setup_logger

logger = setup_logger("position_allocator")


class PositionAllocator:
    """
    Allocates capital across multiple strategies
    Uses confidence-weighted allocation
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_portfolio_risk_pct = config.get('risk', {}).get('max_portfolio_risk_pct', 20.0)
        self.max_position_size_pct = config.get('trading', {}).get('max_position_size_pct', 1.0)
        
    def allocate(
        self,
        signals: List[Dict[str, Any]],
        capital: float,
        current_positions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Allocate positions across strategies
        
        Args:
            signals: List of signals from all strategies
            capital: Available capital
            current_positions: Current open positions
        
        Returns:
            List of allocated positions
        """
        if not signals:
            return []
        
        # Filter valid signals
        valid_signals = [s for s in signals if s and s.get('action') != 'FLAT']
        
        if not valid_signals:
            return []
        
        # Calculate weights for each signal
        weights = self._calculate_weights(valid_signals)
        
        # Allocate positions
        allocated_positions = []
        
        for signal, weight in zip(valid_signals, weights):
            if weight <= 0:
                continue
            
            # Calculate position size
            position_size = self._calculate_position_size(
                signal=signal,
                weight=weight,
                capital=capital,
                current_positions=current_positions
            )
            
            if position_size > 0:
                allocated_positions.append({
                    'symbol': signal.get('symbol'),
                    'strategy': signal.get('strategy'),
                    'action': signal.get('action'),
                    'entry_price': signal.get('entry_price'),
                    'position_size': position_size,
                    'stop_loss': signal.get('stop_loss'),
                    'take_profit': signal.get('take_profit'),
                    'confidence': signal.get('confidence'),
                    'weight': weight,
                    'expected_return': signal.get('expected_return'),
                    'expected_risk': signal.get('expected_risk'),
                    'reason': signal.get('reason')
                })
        
        logger.info(f"[ALLOCATOR] Allocated {len(allocated_positions)} positions from {len(valid_signals)} signals")
        
        return allocated_positions
    
    def _calculate_weights(self, signals: List[Dict[str, Any]]) -> np.ndarray:
        """
        Calculate weights for each signal using formula:
        raw = conf * max(0, exp_ret) / (exp_risk + 1e-8)
        weight = raw / sum(raw)
        """
        if not signals:
            return np.array([])
        
        raw_weights = []
        
        for signal in signals:
            confidence = signal.get('confidence', 0.0)
            exp_return = signal.get('expected_return', 0.0)
            exp_risk = signal.get('expected_risk', 0.0)
            
            # Calculate raw weight
            raw = confidence * max(0, exp_return) / (exp_risk + 1e-8)
            raw_weights.append(raw)
        
        raw_weights = np.array(raw_weights)
        
        # Normalize
        total = np.sum(raw_weights)
        if total > 0:
            weights = raw_weights / total
        else:
            # Equal weights if all raw weights are zero
            weights = np.ones(len(signals)) / len(signals)
        
        return weights
    
    def _calculate_position_size(
        self,
        signal: Dict[str, Any],
        weight: float,
        capital: float,
        current_positions: List[Dict[str, Any]]
    ) -> float:
        """Calculate position size for a signal"""
        try:
            # Base position size from weight
            base_size = capital * weight
            
            # Apply max position size limit
            max_size = capital * self.max_position_size_pct
            base_size = min(base_size, max_size)
            
            # Calculate in base currency units
            entry_price = signal.get('entry_price', 0)
            if entry_price <= 0:
                return 0.0
            
            position_size = base_size / entry_price
            
            # Check portfolio risk
            total_risk = self._calculate_total_risk(current_positions, signal)
            if total_risk > self.max_portfolio_risk_pct:
                # Reduce position size
                risk_ratio = self.max_portfolio_risk_pct / total_risk
                position_size *= risk_ratio
            
            return max(0.0, position_size)
            
        except Exception as e:
            logger.error(f"[ERROR] Error calculating position size: {e}")
            return 0.0
    
    def _calculate_total_risk(
        self,
        current_positions: List[Dict[str, Any]],
        new_signal: Dict[str, Any]
    ) -> float:
        """Calculate total portfolio risk"""
        total_risk = 0.0
        
        # Risk from current positions
        for pos in current_positions:
            pos_value = pos.get('position_size', 0) * pos.get('entry_price', 0)
            stop_loss_pct = abs((pos.get('stop_loss', 0) - pos.get('entry_price', 0)) / pos.get('entry_price', 0) * 100)
            risk = (pos_value * stop_loss_pct / 100) if pos_value > 0 else 0.0
            total_risk += risk
        
        # Risk from new position
        entry_price = new_signal.get('entry_price', 0)
        stop_loss = new_signal.get('stop_loss', 0)
        if entry_price > 0:
            stop_loss_pct = abs((stop_loss - entry_price) / entry_price * 100)
            # Estimate position size (will be calculated properly later)
            estimated_position_value = entry_price * 0.01  # 1% of capital estimate
            risk = estimated_position_value * stop_loss_pct / 100
            total_risk += risk
        
        # Convert to percentage
        # Assuming capital is available
        total_risk_pct = (total_risk / 100) * 100  # Simplified
        
        return total_risk_pct

