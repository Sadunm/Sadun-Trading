"""
Calculate ACTUAL profit after all costs (fees, slippage, spread)
"""
from typing import Dict
from core.fee_calculator import FeeCalculator
from core.slippage_simulator import SlippageSimulator, SpreadSimulator
from utils.validators import validate_price, safe_divide, safe_multiply
from utils.logger import setup_logger

logger = setup_logger("profit_calculator")


class ProfitCalculator:
    """Calculate ACTUAL profit after all costs"""
    
    def __init__(self, trading_type: str = 'spot', use_maker: bool = False, exchange: str = 'bybit'):
        self.exchange = exchange
        self.fee_calc = FeeCalculator(trading_type, use_maker, exchange=exchange)
        self.slippage_sim = SlippageSimulator()
        self.spread_sim = SpreadSimulator()
        self.trading_type = trading_type
    
    def calculate_net_profit(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        quantity: float,
        action: str,  # 'BUY' or 'SELL'
        volatility: float = 0.0
    ) -> Dict[str, float]:
        """
        Calculate net profit after ALL costs
        
        Returns:
            {
                'gross_profit': float,
                'entry_fee': float,
                'exit_fee': float,
                'entry_slippage': float,
                'exit_slippage': float,
                'spread_cost': float,
                'total_costs': float,
                'net_profit': float,
                'profit_pct': float
            }
        """
        try:
            # Validate inputs
            if not all(validate_price(p) for p in [entry_price, exit_price, quantity]):
                return self._empty_result()
            
            # Position value
            position_value = quantity * entry_price
            
            # Calculate fees
            entry_fee = self.fee_calc.calculate_entry_fee(position_value)
            exit_value = quantity * exit_price
            exit_fee = self.fee_calc.calculate_exit_fee(exit_value)
            
            # Calculate slippage (in USD)
            entry_slippage_usd = abs(self.slippage_sim.calculate_slippage(
                symbol, entry_price, action, volatility
            )) * quantity
            
            exit_action = 'SELL' if action == 'BUY' else 'BUY'
            exit_slippage_usd = abs(self.slippage_sim.calculate_slippage(
                symbol, exit_price, exit_action, volatility
            )) * quantity
            
            # Calculate spread cost
            spread = self.spread_sim.get_spread(symbol)
            spread_cost = position_value * spread
            
            # Gross profit
            if action == 'BUY':
                # Bought low, sold high
                gross_profit = quantity * (exit_price - entry_price)
            else:  # SELL (short)
                # Sold high, bought low (short)
                gross_profit = quantity * (entry_price - exit_price)
            
            # Total costs
            total_costs = entry_fee + exit_fee + entry_slippage_usd + exit_slippage_usd + spread_cost
            
            # Net profit
            net_profit = gross_profit - total_costs
            
            # Profit percentage (on position value)
            profit_pct = safe_divide(net_profit, position_value, 0.0) * 100.0
            
            return {
                'gross_profit': gross_profit,
                'entry_fee': entry_fee,
                'exit_fee': exit_fee,
                'entry_slippage': entry_slippage_usd,
                'exit_slippage': exit_slippage_usd,
                'spread_cost': spread_cost,
                'total_costs': total_costs,
                'net_profit': net_profit,
                'profit_pct': profit_pct
            }
            
        except Exception as e:
            logger.error(f"[ERROR] Error calculating net profit: {e}", exc_info=True)
            return self._empty_result()
    
    def _empty_result(self) -> Dict[str, float]:
        """Return empty result dict"""
        return {
            'gross_profit': 0.0,
            'entry_fee': 0.0,
            'exit_fee': 0.0,
            'entry_slippage': 0.0,
            'exit_slippage': 0.0,
            'spread_cost': 0.0,
            'total_costs': 0.0,
            'net_profit': 0.0,
            'profit_pct': 0.0
        }

