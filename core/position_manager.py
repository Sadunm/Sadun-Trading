"""
Thread-safe position manager
"""
from threading import Lock
from datetime import datetime
from typing import Dict, List, Optional
from utils.validators import validate_price, validate_quantity, validate_stop_loss_take_profit
from utils.logger import setup_logger

logger = setup_logger("position_manager")


class Position:
    """Represents a trading position"""
    
    def __init__(self, symbol: str, strategy: str, action: str, entry_price: float, 
                 quantity: float, stop_loss: float, take_profit: float):
        # Validate all inputs
        if not validate_price(entry_price):
            raise ValueError(f"Invalid entry price: {entry_price}")
        if not validate_quantity(quantity):
            raise ValueError(f"Invalid quantity: {quantity}")
        
        self.symbol = symbol
        self.strategy = strategy
        self.action = action.upper()  # BUY or SELL
        self.entry_price = entry_price
        self.quantity = quantity
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.entry_time = datetime.now()
        self.exit_price = None
        self.exit_time = None
        self.pnl = 0.0
        self.pnl_pct = 0.0
        self.status = 'OPEN'
        self.exit_reason = None
    
    def close(self, exit_price: float, exit_reason: str, fees: float = 0.0):
        """Close the position and calculate P&L"""
        from utils.validators import safe_divide
        
        if not validate_price(exit_price):
            raise ValueError(f"Invalid exit price: {exit_price}")
        
        self.exit_price = exit_price
        self.exit_time = datetime.now()
        self.exit_reason = exit_reason
        self.status = 'CLOSED'
        
        # Calculate P&L
        if self.action == 'BUY':
            self.pnl = (exit_price - self.entry_price) * self.quantity - fees
            self.pnl_pct = safe_divide(
                (exit_price - self.entry_price),
                self.entry_price,
                0.0
            ) * 100
        else:  # SELL
            self.pnl = (self.entry_price - exit_price) * self.quantity - fees
            self.pnl_pct = safe_divide(
                (self.entry_price - exit_price),
                self.entry_price,
                0.0
            ) * 100
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'symbol': self.symbol,
            'strategy': self.strategy,
            'action': self.action,
            'entry_price': self.entry_price,
            'quantity': self.quantity,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'entry_time': self.entry_time.isoformat(),
            'exit_price': self.exit_price,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'pnl': self.pnl,
            'pnl_pct': self.pnl_pct,
            'status': self.status,
            'exit_reason': self.exit_reason
        }


class PositionManager:
    """Thread-safe position manager"""
    
    def __init__(self):
        self.positions: Dict[str, Position] = {}  # symbol+strategy as key
        self.lock = Lock()
    
    def open_position(self, symbol: str, strategy: str, action: str, entry_price: float, 
                     quantity: float, stop_loss: float, take_profit: float) -> bool:
        """Open a new position (thread-safe)"""
        try:
            key = f"{symbol}_{strategy}"
            
            with self.lock:
                # Check if already exists
                if key in self.positions:
                    logger.warning(f"[WARN] Position already exists: {key}")
                    return False
                
                # Validate stop loss/take profit
                valid, error = validate_stop_loss_take_profit(entry_price, stop_loss, take_profit, action)
                if not valid:
                    logger.error(f"[ERROR] Invalid stop loss/take profit: {error}")
                    return False
                
                # Create position
                position = Position(
                    symbol=symbol,
                    strategy=strategy,
                    action=action,
                    entry_price=entry_price,
                    quantity=quantity,
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
                
                self.positions[key] = position
                logger.info(f"[OK] Opened {action} position: {symbol} @ ${entry_price:.2f} qty={quantity:.6f}")
                return True
                
        except Exception as e:
            logger.error(f"[ERROR] Error opening position: {e}", exc_info=True)
            return False
    
    def close_position(self, symbol: str, strategy: str, exit_price: float, 
                      exit_reason: str, fees: float = 0.0) -> Optional[Position]:
        """Close an existing position (thread-safe)"""
        try:
            key = f"{symbol}_{strategy}"
            
            with self.lock:
                if key not in self.positions:
                    logger.warning(f"[WARN] Position not found: {key}")
                    return None
                
                position = self.positions[key]
                position.close(exit_price, exit_reason, fees)
                
                # Remove from open positions
                del self.positions[key]
                
                logger.info(f"[OK] Closed position: {symbol} P&L=${position.pnl:.2f} ({position.pnl_pct:.2f}%)")
                return position
                
        except Exception as e:
            logger.error(f"[ERROR] Error closing position: {e}", exc_info=True)
            return None
    
    def get_position(self, symbol: str, strategy: str) -> Optional[Position]:
        """Get position by symbol and strategy"""
        key = f"{symbol}_{strategy}"
        with self.lock:
            return self.positions.get(key)
    
    def has_position(self, symbol: str, strategy: Optional[str] = None) -> bool:
        """Check if position exists"""
        with self.lock:
            if strategy:
                key = f"{symbol}_{strategy}"
                return key in self.positions
            else:
                return any(pos.symbol == symbol for pos in self.positions.values())
    
    def get_all_positions(self) -> List[Position]:
        """Get all open positions"""
        with self.lock:
            return list(self.positions.values())
    
    def get_open_positions_count(self) -> int:
        """Get count of open positions"""
        with self.lock:
            return len(self.positions)

