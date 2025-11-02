"""
Real market slippage simulation
"""
from typing import Dict
from utils.validators import validate_price, clamp_value
from utils.logger import setup_logger

logger = setup_logger("slippage")


class SlippageSimulator:
    """Simulate REAL market slippage"""
    
    # Slippage by coin liquidity
    SLIPPAGE_RATES = {
        'BTCUSDT': 0.0002,   # 0.02% - highest liquidity
        'ETHUSDT': 0.0002,   # 0.02%
        'BNBUSDT': 0.0003,   # 0.03%
        'SOLUSDT': 0.0004,   # 0.04%
        'XRPUSDT': 0.0004,   # 0.04%
        'ADAUSDT': 0.0005,   # 0.05%
        'DOGEUSDT': 0.0005,  # 0.05%
        'MATICUSDT': 0.0005, # 0.05%
        'default': 0.0005    # 0.05% for others
    }
    
    def __init__(self):
        pass
    
    def calculate_slippage(
        self,
        symbol: str,
        price: float,
        action: str,  # 'BUY' or 'SELL'
        volatility: float = 0.0  # Current volatility (0-1)
    ) -> float:
        """
        Calculate realistic slippage
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            price: Current price
            action: 'BUY' or 'SELL'
            volatility: Current market volatility (0-1)
        
        Returns: Slippage amount in USD
        """
        try:
            if not validate_price(price):
                return 0.0
            
            # Get base slippage rate
            base_rate = self.SLIPPAGE_RATES.get(symbol.upper(), self.SLIPPAGE_RATES['default'])
            
            # Adjust for volatility (higher volatility = more slippage)
            volatility_multiplier = 1.0 + (volatility * 0.5)  # Max 50% increase
            slippage_rate = base_rate * volatility_multiplier
            
            # Clamp to reasonable range
            slippage_rate = clamp_value(slippage_rate, 0.0001, 0.002)  # 0.01% to 0.2%
            
            # Calculate slippage
            if action.upper() == 'BUY':
                # Buy at higher price (slippage up)
                slippage = price * slippage_rate
            else:  # SELL
                # Sell at lower price (slippage down)
                slippage = -price * slippage_rate
            
            return slippage
            
        except Exception as e:
            logger.error(f"[ERROR] Error calculating slippage: {e}")
            return 0.0
    
    def apply_slippage(
        self,
        symbol: str,
        intended_price: float,
        action: str,
        volatility: float = 0.0
    ) -> float:
        """
        Apply slippage to get actual execution price
        
        Returns: Actual execution price (after slippage)
        """
        try:
            slippage = self.calculate_slippage(symbol, intended_price, action, volatility)
            
            if action.upper() == 'BUY':
                actual_price = intended_price + slippage  # Pay more
            else:  # SELL
                actual_price = intended_price + slippage  # slippage is negative, so get less
            
            return max(0.0, actual_price)
            
        except Exception as e:
            logger.error(f"[ERROR] Error applying slippage: {e}")
            return intended_price


class SpreadSimulator:
    """Simulate bid-ask spread"""
    
    SPREAD_RATES = {
        'BTCUSDT': 0.0003,   # 0.03% - tight spread
        'ETHUSDT': 0.0004,   # 0.04%
        'BNBUSDT': 0.0005,   # 0.05%
        'SOLUSDT': 0.0006,   # 0.06%
        'XRPUSDT': 0.0007,   # 0.07%
        'ADAUSDT': 0.0008,   # 0.08%
        'DOGEUSDT': 0.0008,  # 0.08%
        'MATICUSDT': 0.0008, # 0.08%
        'DOTUSDT': 0.0008,   # 0.08%
        'AVAXUSDT': 0.0008,  # 0.08%
        'LINKUSDT': 0.0008,  # 0.08%
        'NEARUSDT': 0.0009,  # 0.09%
        'OPUSDT': 0.0009,    # 0.09%
        'INJUSDT': 0.0009,   # 0.09%
        'RNDRUSDT': 0.0009,  # 0.09%
        'FTMUSDT': 0.0009,   # 0.09%
        'TIAUSDT': 0.0010,   # 0.10%
        'LTCUSDT': 0.0007,   # 0.07%
        'ATOMUSDT': 0.0008,  # 0.08%
        'SUIUSDT': 0.0010,   # 0.10%
        'default': 0.0010    # 0.10% for others
    }
    
    def get_spread(self, symbol: str) -> float:
        """Get bid-ask spread for symbol"""
        return self.SPREAD_RATES.get(symbol.upper(), self.SPREAD_RATES['default'])
    
    def get_bid_price(self, mid_price: float, symbol: str) -> float:
        """Get bid price (what you sell at)"""
        try:
            spread = self.get_spread(symbol)
            return mid_price * (1 - spread / 2)
        except Exception:
            return mid_price
    
    def get_ask_price(self, mid_price: float, symbol: str) -> float:
        """Get ask price (what you buy at)"""
        try:
            spread = self.get_spread(symbol)
            return mid_price * (1 + spread / 2)
        except Exception:
            return mid_price

