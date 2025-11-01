"""
API routes for dashboard
"""
from flask import jsonify
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger("routes")


def setup_routes(app, bot):
    """Setup Flask routes"""
    
    @app.route('/')
    def dashboard():
        """Serve dashboard HTML"""
        from api.dashboard import get_dashboard_html
        return get_dashboard_html()
    
    @app.route('/api/stats')
    def get_stats():
        """Get bot statistics"""
        try:
            positions = bot.position_manager.get_all_positions()
            closed_trades = bot.trade_storage.get_all_trades()
            
            current_capital = bot.current_capital
            initial_capital = bot.initial_capital
            total_pnl = current_capital - initial_capital
            
            # Calculate net total PnL (after all costs)
            net_total_pnl = sum(t.get('net_profit', t.get('pnl', 0.0)) for t in closed_trades)
            
            return jsonify({
                'current_capital': current_capital,
                'initial_capital': initial_capital,
                'total_pnl': net_total_pnl,  # Use net profit
                'open_positions': len(positions),
                'total_trades': len(closed_trades),
                'trading_type': bot.trading_type
            })
        except Exception as e:
            logger.error(f"[ERROR] Error getting stats: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/trades')
    def get_trades():
        """Get trade history"""
        try:
            open_positions = bot.position_manager.get_all_positions()
            closed_trades = bot.trade_storage.get_all_trades()
            
            # Combine open and closed
            all_trades = []
            
            # Add closed trades (use net_profit if available)
            for trade in closed_trades:
                net_profit = trade.get('net_profit', trade.get('pnl', 0.0))
                all_trades.append({
                    'symbol': trade.get('symbol'),
                    'strategy': trade.get('strategy'),
                    'action': trade.get('action'),
                    'entry_price': trade.get('entry_price'),
                    'exit_price': trade.get('exit_price'),
                    'quantity': trade.get('quantity'),
                    'pnl': net_profit,  # Use net profit (after costs)
                    'pnl_pct': trade.get('pnl_pct', 0.0),
                    'status': 'CLOSED',
                    'entry_time': trade.get('entry_time'),
                    'total_costs': trade.get('total_costs', 0.0)
                })
            
            # Add open positions
            for pos in open_positions:
                all_trades.append({
                    'symbol': pos.symbol,
                    'strategy': pos.strategy,
                    'action': pos.action,
                    'entry_price': pos.entry_price,
                    'exit_price': None,
                    'quantity': pos.quantity,
                    'pnl': 0.0,
                    'pnl_pct': 0.0,
                    'status': 'OPEN',
                    'entry_time': pos.entry_time.isoformat()
                })
            
            # Sort by entry time (newest first)
            all_trades.sort(key=lambda x: x['entry_time'], reverse=True)
            
            return jsonify(all_trades[:100])  # Return last 100 trades
        except Exception as e:
            logger.error(f"[ERROR] Error getting trades: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/trades/by-date')
    def get_trades_by_date():
        """Get all trades grouped by date"""
        try:
            closed_trades = bot.trade_storage.get_all_trades()
            
            # Group by date
            trades_by_date = {}
            for trade in closed_trades:
                entry_time = trade.get('entry_time', '')
                trade_date = entry_time.split('T')[0] if 'T' in entry_time else entry_time.split(' ')[0]
                
                if trade_date not in trades_by_date:
                    trades_by_date[trade_date] = []
                
                trades_by_date[trade_date].append({
                    'time': trade.get('entry_time', ''),
                    'symbol': trade.get('symbol', ''),
                    'strategy': trade.get('strategy', ''),
                    'action': trade.get('action', ''),
                    'entry_price': trade.get('entry_price', 0.0),
                    'exit_price': trade.get('exit_price', 0.0),
                    'quantity': trade.get('quantity', 0.0),
                    'profit_usd': trade.get('net_profit', trade.get('pnl', 0.0)),
                    'profit_pct': trade.get('pnl_pct', 0.0),
                    'exit_time': trade.get('exit_time', '')
                })
            
            # Sort dates (newest first)
            sorted_dates = sorted(trades_by_date.keys(), reverse=True)
            
            return jsonify({
                'trades_by_date': {
                    date: trades_by_date[date] for date in sorted_dates
                },
                'total_days': len(sorted_dates),
                'dates': sorted_dates
            })
        except Exception as e:
            logger.error(f"[ERROR] Error getting trades by date: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/performance/daily')
    def get_daily_performance():
        """Get daily performance summary"""
        try:
            closed_trades = bot.trade_storage.get_all_trades()
            
            # Group by date and calculate metrics
            daily_stats = {}
            
            for trade in closed_trades:
                entry_time = trade.get('entry_time', '')
                trade_date = entry_time.split('T')[0] if 'T' in entry_time else entry_time.split(' ')[0]
                profit = trade.get('net_profit', trade.get('pnl', 0.0))
                strategy = trade.get('strategy', '')
                
                if trade_date not in daily_stats:
                    daily_stats[trade_date] = {
                        'date': trade_date,
                        'total_trades': 0,
                        'winning_trades': 0,
                        'losing_trades': 0,
                        'total_profit': 0.0,
                        'strategies_used': set(),
                        'symbols_traded': set()
                    }
                
                stats = daily_stats[trade_date]
                stats['total_trades'] += 1
                stats['total_profit'] += profit
                
                if profit > 0:
                    stats['winning_trades'] += 1
                else:
                    stats['losing_trades'] += 1
                
                stats['strategies_used'].add(strategy)
                stats['symbols_traded'].add(trade.get('symbol', ''))
            
            # Calculate win rate and convert sets to lists
            result = []
            for date, stats in sorted(daily_stats.items(), reverse=True):
                win_rate = (stats['winning_trades'] / stats['total_trades'] * 100) if stats['total_trades'] > 0 else 0
                
                result.append({
                    'date': stats['date'],
                    'trades': stats['total_trades'],
                    'wins': stats['winning_trades'],
                    'losses': stats['losing_trades'],
                    'win_rate': round(win_rate, 2),
                    'profit': round(stats['total_profit'], 2),
                    'strategies': list(stats['strategies_used']),
                    'symbols': list(stats['symbols_traded']),
                    'avg_profit_per_trade': round(stats['total_profit'] / stats['total_trades'], 2) if stats['total_trades'] > 0 else 0.0
                })
            
            return jsonify({'daily_performance': result})
        except Exception as e:
            logger.error(f"[ERROR] Error getting daily performance: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/performance/strategy')
    def get_strategy_performance():
        """Get performance breakdown by strategy"""
        try:
            closed_trades = bot.trade_storage.get_all_trades()
            
            # Group by strategy
            strategy_stats = {}
            
            for trade in closed_trades:
                strategy = trade.get('strategy', 'unknown')
                profit = trade.get('net_profit', trade.get('pnl', 0.0))
                
                if strategy not in strategy_stats:
                    strategy_stats[strategy] = {
                        'strategy': strategy,
                        'total_trades': 0,
                        'winning_trades': 0,
                        'losing_trades': 0,
                        'total_profit': 0.0,
                        'profits': [],
                        'losses': []
                    }
                
                stats = strategy_stats[strategy]
                stats['total_trades'] += 1
                stats['total_profit'] += profit
                if profit > 0:
                    stats['profits'].append(profit)
                    stats['winning_trades'] += 1
                else:
                    stats['losses'].append(profit)
                    stats['losing_trades'] += 1
            
            # Calculate metrics
            result = []
            for strategy, stats in strategy_stats.items():
                win_rate = (stats['winning_trades'] / stats['total_trades'] * 100) if stats['total_trades'] > 0 else 0
                avg_profit = sum(stats['profits']) / len(stats['profits']) if stats['profits'] else 0.0
                avg_loss = sum(stats['losses']) / len(stats['losses']) if stats['losses'] else 0.0
                profit_factor = abs(sum(stats['profits']) / sum(stats['losses'])) if stats['losses'] and sum(stats['losses']) != 0 else 0.0
                
                result.append({
                    'strategy': strategy,
                    'total_trades': stats['total_trades'],
                    'wins': stats['winning_trades'],
                    'losses': stats['losing_trades'],
                    'win_rate': round(win_rate, 2),
                    'total_profit': round(stats['total_profit'], 2),
                    'avg_profit': round(avg_profit, 2),
                    'avg_loss': round(avg_loss, 2),
                    'profit_factor': round(profit_factor, 2),
                    'avg_profit_per_trade': round(stats['total_profit'] / stats['total_trades'], 2) if stats['total_trades'] > 0 else 0.0
                })
            
            # Sort by total profit (descending)
            result.sort(key=lambda x: x['total_profit'], reverse=True)
            
            return jsonify({'strategy_performance': result})
        except Exception as e:
            logger.error(f"[ERROR] Error getting strategy performance: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/performance/mdd')
    def get_max_drawdown():
        """Calculate Maximum Drawdown (MDD)"""
        try:
            closed_trades = bot.trade_storage.get_all_trades()
            
            # Calculate cumulative equity curve
            initial_capital = bot.initial_capital
            current_capital = initial_capital
            
            equity_curve = [initial_capital]
            peak_capital = initial_capital
            max_drawdown_pct = 0.0
            max_drawdown_usd = 0.0
            
            # Sort trades by time
            sorted_trades = sorted(closed_trades, key=lambda x: x.get('entry_time', ''))
            
            for trade in sorted_trades:
                profit = trade.get('net_profit', trade.get('pnl', 0.0))
                current_capital += profit
                equity_curve.append(current_capital)
                
                # Update peak
                if current_capital > peak_capital:
                    peak_capital = current_capital
                
                # Calculate drawdown
                drawdown_usd = peak_capital - current_capital
                drawdown_pct = (drawdown_usd / peak_capital * 100) if peak_capital > 0 else 0.0
                
                # Update max drawdown
                if drawdown_pct > max_drawdown_pct:
                    max_drawdown_pct = drawdown_pct
                    max_drawdown_usd = drawdown_usd
            
            return jsonify({
                'max_drawdown_pct': round(max_drawdown_pct, 2),
                'max_drawdown_usd': round(max_drawdown_usd, 2),
                'peak_capital': round(peak_capital, 2),
                'current_capital': round(current_capital, 2),
                'equity_curve': equity_curve
            })
        except Exception as e:
            logger.error(f"[ERROR] Error calculating MDD: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/performance/summary')
    def get_performance_summary():
        """Get overall performance summary"""
        try:
            closed_trades = bot.trade_storage.get_all_trades()
            
            # Calculate totals
            total_trades = len(closed_trades)
            profits = [t.get('net_profit', t.get('pnl', 0.0)) for t in closed_trades if t.get('net_profit', t.get('pnl', 0.0)) > 0]
            losses = [t.get('net_profit', t.get('pnl', 0.0)) for t in closed_trades if t.get('net_profit', t.get('pnl', 0.0)) < 0]
            winning_trades = len(profits)
            losing_trades = len(losses)
            
            total_profit = sum(t.get('net_profit', t.get('pnl', 0.0)) for t in closed_trades)
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            avg_profit = sum(profits) / len(profits) if profits else 0.0
            avg_loss = sum(losses) / len(losses) if losses else 0.0
            profit_factor = abs(sum(profits) / sum(losses)) if losses and sum(losses) != 0 else 0.0
            
            # Get MDD
            initial_capital = bot.initial_capital
            current_capital = initial_capital + total_profit
            equity_curve = [initial_capital]
            peak_capital = initial_capital
            
            sorted_trades = sorted(closed_trades, key=lambda x: x.get('entry_time', ''))
            for trade in sorted_trades:
                profit = trade.get('net_profit', trade.get('pnl', 0.0))
                equity_curve.append(equity_curve[-1] + profit)
                if equity_curve[-1] > peak_capital:
                    peak_capital = equity_curve[-1]
            
            max_drawdown_usd = peak_capital - min(equity_curve) if equity_curve else 0.0
            max_drawdown_pct = (max_drawdown_usd / peak_capital * 100) if peak_capital > 0 else 0.0
            
            return jsonify({
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': round(win_rate, 2),
                'total_profit': round(total_profit, 2),
                'avg_profit': round(avg_profit, 2),
                'avg_loss': round(avg_loss, 2),
                'profit_factor': round(profit_factor, 2),
                'max_drawdown_pct': round(max_drawdown_pct, 2),
                'max_drawdown_usd': round(max_drawdown_usd, 2),
                'initial_capital': round(initial_capital, 2),
                'current_capital': round(current_capital, 2),
                'roi_pct': round((total_profit / initial_capital * 100) if initial_capital > 0 else 0, 2)
            })
        except Exception as e:
            logger.error(f"[ERROR] Error getting performance summary: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/compounding')
    def get_compounding_stats():
        """Get auto compounding statistics"""
        try:
            stats = bot.compound_manager.get_stats()
            
            return jsonify({
                'enabled': stats['enabled'],
                'threshold': stats['threshold'],
                'accumulated': stats['accumulated_profits'],
                'total_compounded': stats['total_compounded'],
                'compound_count': stats['compound_count'],
                'next_compound_date': stats['last_compound_date'],
                'capital_growth': {
                    'initial': bot.initial_capital,
                    'current': bot.current_capital,
                    'growth_pct': ((bot.current_capital - bot.initial_capital) / bot.initial_capital * 100) if bot.initial_capital > 0 else 0.0
                }
            })
        except Exception as e:
            logger.error(f"[ERROR] Error getting compounding stats: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/health')
    def health():
        """Health check endpoint"""
        return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

