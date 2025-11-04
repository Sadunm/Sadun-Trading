"""
Trade Analyzer - Analyzes bot data (isolated)
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict
from utils.logger import setup_logger

logger = setup_logger("monitor_analyzer")


class TradeAnalyzer:
    """Analyzes trading bot data - completely isolated"""
    
    def __init__(self):
        self.analysis_history = []
        
    def analyze_trades(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trade history"""
        if not trades:
            return self._empty_analysis()
        
        # Filter closed trades
        closed_trades = [t for t in trades if t.get('status') == 'CLOSED']
        open_trades = [t for t in trades if t.get('status') == 'OPEN']
        
        if not closed_trades:
            return {
                'total_trades': len(open_trades),
                'closed_trades': 0,
                'open_trades': len(open_trades),
                'message': 'No closed trades yet'
            }
        
        # Calculate metrics
        winning_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in closed_trades if t.get('pnl', 0) < 0]
        
        total_profit = sum(t.get('pnl', 0) for t in winning_trades)
        total_loss = abs(sum(t.get('pnl', 0) for t in losing_trades))
        
        win_rate = (len(winning_trades) / len(closed_trades) * 100) if closed_trades else 0.0
        profit_factor = (total_profit / total_loss) if total_loss > 0 else 0.0
        
        # Strategy breakdown
        strategy_stats = defaultdict(lambda: {'trades': 0, 'wins': 0, 'losses': 0, 'profit': 0.0})
        for trade in closed_trades:
            strategy = trade.get('strategy', 'unknown')
            strategy_stats[strategy]['trades'] += 1
            if trade.get('pnl', 0) > 0:
                strategy_stats[strategy]['wins'] += 1
                strategy_stats[strategy]['profit'] += trade.get('pnl', 0)
            else:
                strategy_stats[strategy]['losses'] += 1
                strategy_stats[strategy]['profit'] += trade.get('pnl', 0)
        
        # Time analysis
        hourly_stats = self._analyze_by_hour(closed_trades)
        daily_stats = self._analyze_by_day(closed_trades)
        
        return {
            'total_trades': len(closed_trades),
            'open_trades': len(open_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_profit': total_profit,
            'total_loss': total_loss,
            'net_profit': total_profit - total_loss,
            'profit_factor': profit_factor,
            'avg_profit_per_trade': total_profit / len(winning_trades) if winning_trades else 0.0,
            'avg_loss_per_trade': total_loss / len(losing_trades) if losing_trades else 0.0,
            'strategy_breakdown': dict(strategy_stats),
            'hourly_performance': hourly_stats,
            'daily_performance': daily_stats,
            'best_trade': max(closed_trades, key=lambda t: t.get('pnl', 0)) if closed_trades else None,
            'worst_trade': min(closed_trades, key=lambda t: t.get('pnl', 0)) if closed_trades else None
        }
    
    def _analyze_by_hour(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance by hour of day"""
        hourly = defaultdict(lambda: {'trades': 0, 'profit': 0.0, 'wins': 0, 'losses': 0})
        
        for trade in trades:
            try:
                entry_time = datetime.fromisoformat(trade.get('entry_time', '').replace('Z', '+00:00'))
                hour = entry_time.hour
                hourly[hour]['trades'] += 1
                hourly[hour]['profit'] += trade.get('pnl', 0)
                if trade.get('pnl', 0) > 0:
                    hourly[hour]['wins'] += 1
                else:
                    hourly[hour]['losses'] += 1
            except Exception:
                continue
        
        return dict(hourly)
    
    def _analyze_by_day(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance by day"""
        daily = defaultdict(lambda: {'trades': 0, 'profit': 0.0, 'wins': 0, 'losses': 0})
        
        for trade in trades:
            try:
                entry_time = datetime.fromisoformat(trade.get('entry_time', '').replace('Z', '+00:00'))
                day = entry_time.date().isoformat()
                daily[day]['trades'] += 1
                daily[day]['profit'] += trade.get('pnl', 0)
                if trade.get('pnl', 0) > 0:
                    daily[day]['wins'] += 1
                else:
                    daily[day]['losses'] += 1
            except Exception:
                continue
        
        return dict(daily)
    
    def _empty_analysis(self) -> Dict[str, Any]:
        """Return empty analysis structure"""
        return {
            'total_trades': 0,
            'closed_trades': 0,
            'open_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'total_profit': 0.0,
            'total_loss': 0.0,
            'net_profit': 0.0,
            'profit_factor': 0.0,
            'message': 'No trades available'
        }
    
    def analyze_signals(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trading signals"""
        if not signals:
            return {'total_signals': 0, 'message': 'No signals available'}
        
        # Group by strategy
        strategy_signals = defaultdict(int)
        action_signals = defaultdict(int)
        
        for signal in signals:
            strategy = signal.get('strategy', 'unknown')
            action = signal.get('action', 'unknown')
            strategy_signals[strategy] += 1
            action_signals[action] += 1
        
        return {
            'total_signals': len(signals),
            'by_strategy': dict(strategy_signals),
            'by_action': dict(action_signals),
            'latest_signals': signals[-10:] if len(signals) > 10 else signals
        }
    
    def detect_patterns(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect trading patterns"""
        patterns = {
            'winning_streak': 0,
            'losing_streak': 0,
            'current_streak': 0,
            'streak_type': 'none',
            'best_hour': None,
            'worst_hour': None,
            'best_strategy': None,
            'worst_strategy': None
        }
        
        if not trades:
            return patterns
        
        closed_trades = [t for t in trades if t.get('status') == 'CLOSED']
        if not closed_trades:
            return patterns
        
        # Calculate streaks
        current_streak = 0
        streak_type = 'none'
        max_win_streak = 0
        max_loss_streak = 0
        
        for trade in closed_trades:
            pnl = trade.get('pnl', 0)
            if pnl > 0:
                if streak_type == 'win':
                    current_streak += 1
                else:
                    if streak_type == 'loss':
                        max_loss_streak = max(max_loss_streak, abs(current_streak))
                    current_streak = 1
                    streak_type = 'win'
            else:
                if streak_type == 'loss':
                    current_streak -= 1
                else:
                    if streak_type == 'win':
                        max_win_streak = max(max_win_streak, current_streak)
                    current_streak = -1
                    streak_type = 'loss'
        
        patterns['winning_streak'] = max_win_streak
        patterns['losing_streak'] = max_loss_streak
        patterns['current_streak'] = abs(current_streak)
        patterns['streak_type'] = streak_type
        
        # Find best/worst hours
        hourly_stats = self._analyze_by_hour(closed_trades)
        if hourly_stats:
            best_hour = max(hourly_stats.items(), key=lambda x: x[1]['profit'])
            worst_hour = min(hourly_stats.items(), key=lambda x: x[1]['profit'])
            patterns['best_hour'] = best_hour[0]
            patterns['worst_hour'] = worst_hour[0]
        
        # Find best/worst strategies
        strategy_stats = defaultdict(lambda: {'profit': 0.0, 'trades': 0})
        for trade in closed_trades:
            strategy = trade.get('strategy', 'unknown')
            strategy_stats[strategy]['profit'] += trade.get('pnl', 0)
            strategy_stats[strategy]['trades'] += 1
        
        if strategy_stats:
            best_strategy = max(strategy_stats.items(), key=lambda x: x[1]['profit'])
            worst_strategy = min(strategy_stats.items(), key=lambda x: x[1]['profit'])
            patterns['best_strategy'] = best_strategy[0]
            patterns['worst_strategy'] = worst_strategy[0]
        
        return patterns

