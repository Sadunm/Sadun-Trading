"""
Trade history storage to CSV
"""
import csv
import os
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from utils.logger import setup_logger

logger = setup_logger("storage")


class TradeStorage:
    """Store and retrieve trade history to/from CSV"""
    
    def __init__(self, csv_path: str = "data/trade_history.csv"):
        self.csv_path = Path(csv_path)
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_header()
    
    def _ensure_header(self):
        """Ensure CSV file has header"""
        if not self.csv_path.exists():
            try:
                with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        'symbol', 'strategy', 'action', 'entry_price', 'exit_price',
                        'quantity', 'entry_time', 'exit_time', 'pnl', 'pnl_pct',
                        'status', 'exit_reason', 'stop_loss', 'take_profit',
                        'entry_fee', 'exit_fee', 'entry_slippage', 'exit_slippage',
                        'spread_cost', 'total_costs', 'net_profit'
                    ])
            except Exception as e:
                logger.error(f"[ERROR] Error creating CSV header: {e}")
    
    def save_trade(self, position, profit_data: Optional[Dict] = None):
        """Save closed position to CSV with cost breakdown"""
        try:
            # Extract cost data if available
            if profit_data:
                entry_fee = profit_data.get('entry_fee', 0.0)
                exit_fee = profit_data.get('exit_fee', 0.0)
                entry_slippage = profit_data.get('entry_slippage', 0.0)
                exit_slippage = profit_data.get('exit_slippage', 0.0)
                spread_cost = profit_data.get('spread_cost', 0.0)
                total_costs = profit_data.get('total_costs', 0.0)
                net_profit = profit_data.get('net_profit', position.pnl)
            else:
                # Fallback if profit_data not provided
                entry_fee = 0.0
                exit_fee = 0.0
                entry_slippage = 0.0
                exit_slippage = 0.0
                spread_cost = 0.0
                total_costs = 0.0
                net_profit = position.pnl
            
            with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    position.symbol,
                    position.strategy,
                    position.action,
                    f"{position.entry_price:.8f}",
                    f"{position.exit_price:.8f}" if position.exit_price else "",
                    f"{position.quantity:.8f}",
                    position.entry_time.isoformat(),
                    position.exit_time.isoformat() if position.exit_time else "",
                    f"{position.pnl:.2f}",  # Gross PnL
                    f"{position.pnl_pct:.2f}",  # Gross PnL %
                    position.status,
                    position.exit_reason or "",
                    f"{position.stop_loss:.8f}",
                    f"{position.take_profit:.8f}",
                    f"{entry_fee:.4f}",
                    f"{exit_fee:.4f}",
                    f"{entry_slippage:.4f}",
                    f"{exit_slippage:.4f}",
                    f"{spread_cost:.4f}",
                    f"{total_costs:.4f}",
                    f"{net_profit:.4f}"  # Net profit after all costs
                ])
            logger.info(f"[OK] Trade saved to CSV: {position.symbol} Net P&L=${net_profit:.2f} (Costs: ${total_costs:.2f})")
        except Exception as e:
            logger.error(f"[ERROR] Error saving trade to CSV: {e}", exc_info=True)
    
    def get_all_trades(self) -> List[Dict]:
        """Load all trades from CSV"""
        trades = []
        try:
            if not self.csv_path.exists():
                return trades
            
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        trade_dict = {
                            'symbol': row['symbol'],
                            'strategy': row['strategy'],
                            'action': row['action'],
                            'entry_price': float(row['entry_price']),
                            'exit_price': float(row['exit_price']) if row.get('exit_price') else None,
                            'quantity': float(row['quantity']),
                            'entry_time': row['entry_time'],
                            'exit_time': row.get('exit_time', ''),
                            'pnl': float(row.get('pnl', 0.0)),  # Gross PnL
                            'pnl_pct': float(row.get('pnl_pct', 0.0)),
                            'status': row['status'],
                            'exit_reason': row.get('exit_reason', ''),
                            'stop_loss': float(row['stop_loss']),
                            'take_profit': float(row['take_profit'])
                        }
                        
                        # Add cost breakdown if available (new format)
                        if 'entry_fee' in row:
                            trade_dict['entry_fee'] = float(row.get('entry_fee', 0.0))
                            trade_dict['exit_fee'] = float(row.get('exit_fee', 0.0))
                            trade_dict['entry_slippage'] = float(row.get('entry_slippage', 0.0))
                            trade_dict['exit_slippage'] = float(row.get('exit_slippage', 0.0))
                            trade_dict['spread_cost'] = float(row.get('spread_cost', 0.0))
                            trade_dict['total_costs'] = float(row.get('total_costs', 0.0))
                            trade_dict['net_profit'] = float(row.get('net_profit', trade_dict['pnl']))  # Use net if available
                        else:
                            # Old format - use gross PnL as net
                            trade_dict['net_profit'] = trade_dict['pnl']
                        
                        trades.append(trade_dict)
                    except (ValueError, KeyError) as e:
                        logger.warning(f"[WARN] Skipping invalid row in CSV: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"[ERROR] Error loading trades from CSV: {e}", exc_info=True)
        
        return trades
    
    def get_trades_by_symbol(self, symbol: str) -> List[Dict]:
        """Get trades for specific symbol"""
        all_trades = self.get_all_trades()
        return [t for t in all_trades if t['symbol'] == symbol]
    
    def get_trades_by_strategy(self, strategy: str) -> List[Dict]:
        """Get trades for specific strategy"""
        all_trades = self.get_all_trades()
        return [t for t in all_trades if t['strategy'] == strategy]

