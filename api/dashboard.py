"""
Enhanced Dashboard HTML with Live Matching features
"""


def get_dashboard_html():
    """Get enhanced dashboard HTML"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Badshah Trading Bot - Live Matching Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #0a0e27;
            color: #e0e0e0;
            padding: 20px;
        }
        .container { max-width: 1600px; margin: 0 auto; }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: #1a1f3a;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        .stat-value {
            font-size: 28px;
            font-weight: bold;
            color: #4ade80;
        }
        .stat-label {
            font-size: 12px;
            color: #94a3b8;
            margin-top: 5px;
        }
        .section {
            background: #1a1f3a;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .section-title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 15px;
            color: #667eea;
        }
        .trades-table, .performance-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        th {
            background: #2d3748;
            padding: 12px;
            text-align: left;
            font-size: 12px;
            color: #94a3b8;
        }
        td {
            padding: 12px;
            border-top: 1px solid #2d3748;
            font-size: 13px;
        }
        .positive { color: #4ade80; }
        .negative { color: #f87171; }
        .btn-refresh {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin-bottom: 20px;
        }
        .btn-refresh:hover { background: #5568d3; }
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .tab {
            background: #2d3748;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            border: 2px solid transparent;
        }
        .tab.active {
            background: #667eea;
            border-color: #764ba2;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>[START] Badshah Trading Bot - Live Matching Dashboard</h1>
            <p>Paper Trading = Live Trading (Exact Fee Matching)</p>
        </div>
        
        <button class="btn-refresh" onclick="loadAllData()">[INFO] Refresh All</button>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value" id="capital">$0.00</div>
                <div class="stat-label">Current Capital</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="pnl">$0.00</div>
                <div class="stat-label">Total P&L (Net)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="positions">0</div>
                <div class="stat-label">Open Positions</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="trades">0</div>
                <div class="stat-label">Total Trades</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="win-rate">0%</div>
                <div class="stat-label">Win Rate</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="mdd">0%</div>
                <div class="stat-label">Max Drawdown</div>
            </div>
        </div>
        
        <div class="tabs">
            <div class="tab active" onclick="showTab('performance')">Performance</div>
            <div class="tab" onclick="showTab('trades')">Trade History</div>
            <div class="tab" onclick="showTab('daily')">Daily Summary</div>
            <div class="tab" onclick="showTab('strategy')">Strategy Breakdown</div>
            <div class="tab" onclick="showTab('compounding')">Auto Compounding</div>
        </div>
        
        <!-- Performance Tab -->
        <div id="performance-tab" class="tab-content active">
            <div class="section">
                <div class="section-title">Performance Summary</div>
                <table class="performance-table">
                    <thead>
                        <tr>
                            <th>Metric</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody id="performance-summary-body">
                        <tr><td colspan="2" style="text-align: center;">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- Trades Tab -->
        <div id="trades-tab" class="tab-content">
            <div class="section">
                <div class="section-title">Trade History</div>
                <table class="trades-table">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Time</th>
                            <th>Symbol</th>
                            <th>Strategy</th>
                            <th>Action</th>
                            <th>Entry</th>
                            <th>Exit</th>
                            <th>Profit</th>
                            <th>P/L %</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody id="trades-body">
                        <tr><td colspan="10" style="text-align: center;">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- Daily Tab -->
        <div id="daily-tab" class="tab-content">
            <div class="section">
                <div class="section-title">Daily Performance</div>
                <table class="performance-table">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Trades</th>
                            <th>Wins</th>
                            <th>Losses</th>
                            <th>Win Rate</th>
                            <th>Profit</th>
                            <th>Avg/Trade</th>
                            <th>Strategies</th>
                        </tr>
                    </thead>
                    <tbody id="daily-performance-body">
                        <tr><td colspan="8" style="text-align: center;">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- Strategy Tab -->
        <div id="strategy-tab" class="tab-content">
            <div class="section">
                <div class="section-title">Strategy Performance Breakdown</div>
                <table class="performance-table">
                    <thead>
                        <tr>
                            <th>Strategy</th>
                            <th>Trades</th>
                            <th>Wins</th>
                            <th>Losses</th>
                            <th>Win Rate</th>
                            <th>Total Profit</th>
                            <th>Avg Profit</th>
                            <th>Profit Factor</th>
                        </tr>
                    </thead>
                    <tbody id="strategy-performance-body">
                        <tr><td colspan="8" style="text-align: center;">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- Compounding Tab -->
        <div id="compounding-tab" class="tab-content">
            <div class="section">
                <div class="section-title">Auto Compounding Statistics</div>
                <table class="performance-table">
                    <thead>
                        <tr>
                            <th>Metric</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody id="compounding-body">
                        <tr><td colspan="2" style="text-align: center;">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    
    <script>
        function showTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            
            // Show selected tab
            document.getElementById(tabName + '-tab').classList.add('active');
            event.target.classList.add('active');
            
            // Load tab data
            if (tabName === 'performance') loadPerformanceSummary();
            else if (tabName === 'daily') loadDailyPerformance();
            else if (tabName === 'strategy') loadStrategyPerformance();
            else if (tabName === 'compounding') loadCompounding();
        }
        
        async function loadAllData() {
            await Promise.all([
                loadStats(),
                loadTrades(),
                loadPerformanceSummary(),
                loadDailyPerformance(),
                loadStrategyPerformance(),
                loadCompounding()
            ]);
        }
        
        async function loadStats() {
            try {
                const res = await fetch('/api/stats');
                const stats = await res.json();
                
                document.getElementById('capital').textContent = '$' + stats.current_capital.toFixed(2);
                document.getElementById('pnl').textContent = '$' + stats.total_pnl.toFixed(2);
                document.getElementById('pnl').className = stats.total_pnl >= 0 ? 'stat-value positive' : 'stat-value negative';
                document.getElementById('positions').textContent = stats.open_positions;
                document.getElementById('trades').textContent = stats.total_trades;
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        }
        
        async function loadPerformanceSummary() {
            try {
                const res = await fetch('/api/performance/summary');
                const data = await res.json();
                
                document.getElementById('win-rate').textContent = data.win_rate.toFixed(1) + '%';
                document.getElementById('mdd').textContent = data.max_drawdown_pct.toFixed(2) + '%';
                
                const tbody = document.getElementById('performance-summary-body');
                tbody.innerHTML = `
                    <tr><td>Total Trades</td><td>${data.total_trades}</td></tr>
                    <tr><td>Winning Trades</td><td class="positive">${data.winning_trades}</td></tr>
                    <tr><td>Losing Trades</td><td class="negative">${data.losing_trades}</td></tr>
                    <tr><td>Win Rate</td><td>${data.win_rate.toFixed(2)}%</td></tr>
                    <tr><td>Total Profit</td><td class="${data.total_profit >= 0 ? 'positive' : 'negative'}">$${data.total_profit.toFixed(2)}</td></tr>
                    <tr><td>Avg Profit/Trade</td><td>$${data.avg_profit.toFixed(2)}</td></tr>
                    <tr><td>Avg Loss/Trade</td><td class="negative">$${data.avg_loss.toFixed(2)}</td></tr>
                    <tr><td>Profit Factor</td><td>${data.profit_factor.toFixed(2)}</td></tr>
                    <tr><td>Max Drawdown</td><td class="negative">${data.max_drawdown_pct.toFixed(2)}% ($${data.max_drawdown_usd.toFixed(2)})</td></tr>
                    <tr><td>ROI</td><td class="${data.roi_pct >= 0 ? 'positive' : 'negative'}">${data.roi_pct.toFixed(2)}%</td></tr>
                    <tr><td>Initial Capital</td><td>$${data.initial_capital.toFixed(2)}</td></tr>
                    <tr><td>Current Capital</td><td>$${data.current_capital.toFixed(2)}</td></tr>
                `;
            } catch (error) {
                console.error('Error loading performance summary:', error);
            }
        }
        
        async function loadTrades() {
            try {
                const res = await fetch('/api/trades');
                const trades = await res.json();
                
                const tbody = document.getElementById('trades-body');
                if (trades.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="10" style="text-align: center;">No trades yet</td></tr>';
                    return;
                }
                
                tbody.innerHTML = trades.map(trade => {
                    const entryTime = new Date(trade.entry_time);
                    const dateStr = entryTime.toLocaleDateString();
                    const timeStr = entryTime.toLocaleTimeString();
                    
                    return `
                        <tr>
                            <td>${dateStr}</td>
                            <td>${timeStr}</td>
                            <td>${trade.symbol}</td>
                            <td>${trade.strategy}</td>
                            <td>${trade.action}</td>
                            <td>$${parseFloat(trade.entry_price).toFixed(2)}</td>
                            <td>${trade.exit_price ? '$' + parseFloat(trade.exit_price).toFixed(2) : '-'}</td>
                            <td class="${trade.pnl >= 0 ? 'positive' : 'negative'}">
                                $${parseFloat(trade.pnl).toFixed(2)}
                            </td>
                            <td class="${trade.pnl >= 0 ? 'positive' : 'negative'}">
                                ${parseFloat(trade.pnl_pct).toFixed(2)}%
                            </td>
                            <td>${trade.status}</td>
                        </tr>
                    `;
                }).join('');
            } catch (error) {
                console.error('Error loading trades:', error);
            }
        }
        
        async function loadDailyPerformance() {
            try {
                const res = await fetch('/api/performance/daily');
                const data = await res.json();
                
                const tbody = document.getElementById('daily-performance-body');
                if (data.daily_performance.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No daily data yet</td></tr>';
                    return;
                }
                
                tbody.innerHTML = data.daily_performance.map(day => `
                    <tr>
                        <td>${day.date}</td>
                        <td>${day.trades}</td>
                        <td class="positive">${day.wins}</td>
                        <td class="negative">${day.losses}</td>
                        <td>${day.win_rate.toFixed(1)}%</td>
                        <td class="${day.profit >= 0 ? 'positive' : 'negative'}">$${day.profit.toFixed(2)}</td>
                        <td>$${day.avg_profit_per_trade.toFixed(2)}</td>
                        <td>${day.strategies.join(', ')}</td>
                    </tr>
                `).join('');
            } catch (error) {
                console.error('Error loading daily performance:', error);
            }
        }
        
        async function loadStrategyPerformance() {
            try {
                const res = await fetch('/api/performance/strategy');
                const data = await res.json();
                
                const tbody = document.getElementById('strategy-performance-body');
                if (data.strategy_performance.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No strategy data yet</td></tr>';
                    return;
                }
                
                tbody.innerHTML = data.strategy_performance.map(strat => `
                    <tr>
                        <td><strong>${strat.strategy}</strong></td>
                        <td>${strat.total_trades}</td>
                        <td class="positive">${strat.wins}</td>
                        <td class="negative">${strat.losses}</td>
                        <td>${strat.win_rate.toFixed(1)}%</td>
                        <td class="${strat.total_profit >= 0 ? 'positive' : 'negative'}">$${strat.total_profit.toFixed(2)}</td>
                        <td>$${strat.avg_profit_per_trade.toFixed(2)}</td>
                        <td>${strat.profit_factor.toFixed(2)}</td>
                    </tr>
                `).join('');
            } catch (error) {
                console.error('Error loading strategy performance:', error);
            }
        }
        
        async function loadCompounding() {
            try {
                const res = await fetch('/api/compounding');
                const data = await res.json();
                
                const tbody = document.getElementById('compounding-body');
                tbody.innerHTML = `
                    <tr><td>Auto Compounding</td><td>${data.enabled ? 'ENABLED' : 'DISABLED'}</td></tr>
                    <tr><td>Threshold</td><td>$${data.threshold.toFixed(2)}</td></tr>
                    <tr><td>Accumulated Profits</td><td>$${data.accumulated.toFixed(2)}</td></tr>
                    <tr><td>Total Compounded</td><td class="positive">$${data.total_compounded.toFixed(2)}</td></tr>
                    <tr><td>Compound Count</td><td>${data.compound_count}</td></tr>
                    <tr><td>Initial Capital</td><td>$${data.capital_growth.initial.toFixed(2)}</td></tr>
                    <tr><td>Current Capital</td><td>$${data.capital_growth.current.toFixed(2)}</td></tr>
                    <tr><td>Growth</td><td class="${data.capital_growth.growth_pct >= 0 ? 'positive' : 'negative'}">${data.capital_growth.growth_pct.toFixed(2)}%</td></tr>
                `;
            } catch (error) {
                console.error('Error loading compounding:', error);
            }
        }
        
        // Auto-refresh every 5 seconds
        setInterval(loadAllData, 5000);
        
        // Load on page load
        loadAllData();
    </script>
</body>
</html>
"""
