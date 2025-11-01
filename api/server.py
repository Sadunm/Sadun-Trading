"""
Flask server for dashboard
"""
from flask import Flask
from api.routes import setup_routes
from utils.logger import setup_logger

logger = setup_logger("api_server")

app = Flask(__name__)


def run_server(bot, port: int = 10000, host: str = "0.0.0.0"):
    """Run Flask server"""
    try:
        setup_routes(app, bot)
        logger.info(f"[OK] Dashboard starting on http://{host}:{port}")
        app.run(host=host, port=port, debug=False, threaded=True)
    except Exception as e:
        logger.error(f"[ERROR] Error starting Flask server: {e}", exc_info=True)

