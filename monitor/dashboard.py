"""
Standalone Dashboard for Monitoring System
"""
from flask import Flask, render_template_string, jsonify
from monitor.monitor_service import MonitorService
from monitor.config import MonitorConfig
from utils.logger import setup_logger
import threading

logger = setup_logger("monitor_dashboard")

app = Flask(__name__)

# Global monitor service
monitor_service = None
monitor_thread = None


def init_monitor():
    """Initialize monitor service"""
    global monitor_service, monitor_thread
    config = MonitorConfig()
    monitor_service = MonitorService(config)
    
    # Start monitor in background thread
    monitor_thread = threading.Thread(target=monitor_service.start, daemon=True)
    monitor_thread.start()
    
    logger.info("[INIT] Monitor service initialized")


# Initialize on import
init_monitor()


@app.route('/')
def dashboard():
    """Main dashboard"""
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sadun Trading Bot - Isolated Monitor</title>
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
        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            margin-top: 10px;
        }
        .status-connected { background: #4ade80; color: white; }
        .status-disconnected { background: #f87171; color: white; }
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
        .btn-refresh {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin-bottom: 20px;
        }
        .positive { color: #4ade80; }
        .negative { color: #f87171; }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        th {
            background: #2d3748;
            padding: 12px;
            text-align: left;
            font-size: 12px;
        }
        td {
            padding: 12px;
            border-top: 1px solid #2d3748;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Sadun Trading Bot - Isolated Monitor</h1>
            <p>Completely Separate Monitoring System</p>
            <div id="connection-status" class="status-badge status-disconnected">Checking...</div>
        </div>
        
        <button class="btn-refresh" onclick="loadAllData()">🔄 Refresh All Data</button>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value" id="capital">$0.00</div>
                <div class="stat-label">Current Capital</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="pnl">$0.00</div>
                <div class="stat-label">Total P&L</div>
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
                <div class="stat-value" id="net-profit">$0.00</div>
                <div class="stat-label">Net Profit</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="profit-factor">0.00</div>
                <div class="stat-label">Profit Factor</div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">📊 Analysis & Patterns</div>
            <div id="analysis-content">Loading...</div>
        </div>
        
        <div class="section">
            <div class="section-title">📈 Strategy Performance</div>
            <div id="strategy-content">Loading...</div>
        </div>
        
        <div class="section">
            <div class="section-title">🔗 Connection Info</div>
            <div id="connection-info">Loading...</div>
        </div>
    </div>
    
    <script>
        async function loadAllData() {
            await Promise.all([
                loadStats(),
                loadAnalysis(),
                loadConnectionInfo()
            ]);
        }
        
        async function loadStats() {
            try {
                const res = await fetch('/api/analysis');
                const data = await res.json();
                
                if (data.bot_data && data.bot_data.stats) {
                    const stats = data.bot_data.stats;
                    document.getElementById('capital').textContent = '$' + (stats.current_capital || 0).toFixed(2);
                    document.getElementById('pnl').textContent = '$' + (stats.total_pnl || 0).toFixed(2);
                    document.getElementById('trades').textContent = stats.total_trades || 0;
                }
                
                if (data.analysis) {
                    const analysis = data.analysis;
                    document.getElementById('win-rate').textContent = (analysis.win_rate || 0).toFixed(1) + '%';
                    document.getElementById('net-profit').textContent = '$' + (analysis.net_profit || 0).toFixed(2);
                    document.getElementById('profit-factor').textContent = (analysis.profit_factor || 0).toFixed(2);
                }
                
                // Update connection status
                const status = data.bot_data?.connection_status;
                const statusEl = document.getElementById('connection-status');
                if (status) {
                    statusEl.textContent = '✅ Connected';
                    statusEl.className = 'status-badge status-connected';
                } else {
                    statusEl.textContent = '❌ Disconnected';
                    statusEl.className = 'status-badge status-disconnected';
                }
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        }
        
        async function loadAnalysis() {
            try {
                const res = await fetch('/api/analysis');
                const data = await res.json();
                
                const analysis = data.analysis || {};
                const patterns = data.patterns || {};
                
                let html = '<table><tr><th>Metric</th><th>Value</th></tr>';
                html += `<tr><td>Total Trades</td><td>${analysis.total_trades || 0}</td></tr>`;
                html += `<tr><td>Winning Trades</td><td class="positive">${analysis.winning_trades || 0}</td></tr>`;
                html += `<tr><td>Losing Trades</td><td class="negative">${analysis.losing_trades || 0}</td></tr>`;
                html += `<tr><td>Win Rate</td><td>${(analysis.win_rate || 0).toFixed(2)}%</td></tr>`;
                html += `<tr><td>Net Profit</td><td class="${(analysis.net_profit || 0) >= 0 ? 'positive' : 'negative'}">$${(analysis.net_profit || 0).toFixed(2)}</td></tr>`;
                html += `<tr><td>Profit Factor</td><td>${(analysis.profit_factor || 0).toFixed(2)}</td></tr>`;
                html += `<tr><td>Current Streak</td><td>${patterns.current_streak || 0} ${patterns.streak_type || 'none'}</td></tr>`;
                html += `<tr><td>Best Strategy</td><td>${patterns.best_strategy || 'N/A'}</td></tr>`;
                html += `<tr><td>Best Hour</td><td>${patterns.best_hour !== null ? patterns.best_hour + ':00' : 'N/A'}</td></tr>`;
                html += '</table>';
                
                document.getElementById('analysis-content').innerHTML = html;
            } catch (error) {
                console.error('Error loading analysis:', error);
            }
        }
        
        async function loadConnectionInfo() {
            try {
                const res = await fetch('/api/connection');
                const data = await res.json();
                
                let html = '<table><tr><th>Info</th><th>Value</th></tr>';
                html += `<tr><td>Bot API URL</td><td>${data.api_url || 'N/A'}</td></tr>`;
                html += `<tr><td>Connection Status</td><td>${data.connected ? '✅ Connected' : '❌ Disconnected'}</td></tr>`;
                html += `<tr><td>Last Error</td><td>${data.last_error || 'None'}</td></tr>`;
                html += `<tr><td>Last Update</td><td>${data.timestamp || 'N/A'}</td></tr>`;
                html += '</table>';
                
                document.getElementById('connection-info').innerHTML = html;
            } catch (error) {
                console.error('Error loading connection info:', error);
            }
        }
        
        // Auto-refresh every 3 seconds
        setInterval(loadAllData, 3000);
        
        // Load on page load
        loadAllData();
    </script>
</body>
</html>
    """
    return html


@app.route('/api/analysis')
def get_analysis():
    """Get current analysis"""
    try:
        if monitor_service:
            analysis = monitor_service.get_current_analysis()
            return jsonify(analysis)
        else:
            return jsonify({'error': 'Monitor service not initialized'}), 500
    except Exception as e:
        logger.error(f"[ERROR] Error getting analysis: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/connection')
def get_connection():
    """Get connection status"""
    try:
        if monitor_service:
            connector = monitor_service.connector
            connector.check_connection()
            return jsonify({
                'api_url': connector.api_url,
                'connected': connector.connection_status,
                'last_error': connector.last_error,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({'error': 'Monitor service not initialized'}), 500
    except Exception as e:
        logger.error(f"[ERROR] Error getting connection: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    logger.info("[START] Starting Isolated Monitor Dashboard...")
    logger.info("[INFO] Dashboard will be available at http://localhost:10001")
    logger.info("[INFO] Make sure trading bot is running at http://localhost:10000")
    app.run(host='0.0.0.0', port=10001, debug=False)

