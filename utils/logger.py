"""
Windows-safe logging system
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
        # Try to reconfigure encoding
        try:
            if hasattr(stream, 'reconfigure'):
                stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass
    
    def emit(self, record):
        """Emit a record, replacing problematic Unicode characters"""
        try:
            msg = self.format(record)
            # Replace emojis on Windows
            if sys.platform == 'win32':
                msg = self._replace_emojis(msg)
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except (UnicodeEncodeError, UnicodeError):
            # Fallback: remove problematic characters
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
        replacements = {
            '✅': '[OK]',
            '❌': '[ERROR]',
            '🚀': '[START]',
            '⚠️': '[WARN]',
            '📊': '[INFO]',
            '📈': '[INFO]',
            '📅': '[INFO]',
            '👋': '[STOP]',
            '🛑': '[STOP]',
        }
        for emoji, replacement in replacements.items():
            text = text.replace(emoji, replacement)
        return text


def setup_logger(name="bot", log_level="INFO"):
    """Setup comprehensive logging system"""
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.handlers.clear()  # Remove existing handlers
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler (Windows-safe)
    console_handler = SafeConsoleHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (rotating)
    log_filename = f"logs/bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = RotatingFileHandler(
        log_filename,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

