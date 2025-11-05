"""
Logger utility for AI Trading System
"""
import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime


class SafeConsoleHandler(logging.StreamHandler):
    """Console handler that safely handles Unicode on Windows"""
    
    def __init__(self, stream=None):
        if stream is None:
            stream = sys.stdout
        super().__init__(stream)
        try:
            if hasattr(stream, 'reconfigure'):
                stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass
    
    def emit(self, record):
        """Emit a record, replacing problematic Unicode characters"""
        try:
            msg = self.format(record)
            if sys.platform == 'win32':
                msg = self._replace_emojis(msg)
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except (UnicodeEncodeError, UnicodeError):
            try:
                msg = self.format(record)
                msg = msg.encode('ascii', errors='replace').decode('ascii')
                stream.write(msg + self.terminator)
                self.flush()
            except Exception:
                self.handleError(record)
        except Exception:
            self.handleError(record)
    
    def _replace_emojis(self, text: str) -> str:
        """Replace emojis with ASCII alternatives"""
        emoji_replacements = {
            '✅': '[OK]',
            '❌': '[ERROR]',
            '⚠️': '[WARN]',
            '🚀': '[INFO]',
            '📊': '[DATA]',
        }
        for emoji, replacement in emoji_replacements.items():
            text = text.replace(emoji, replacement)
        return text


def setup_logger(name="bot", log_level="INFO"):
    """Setup comprehensive logging system"""
    # Create logs directory
    log_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.handlers.clear()
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = SafeConsoleHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    log_filename = os.path.join(log_dir, f"ai_bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    file_handler = RotatingFileHandler(
        log_filename,
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

