"""
Configuration loader with YAML support
"""
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from utils.errors import ConfigurationError
from utils.logger import setup_logger

logger = setup_logger("config_loader")

# Global config instance
_config_instance = None


class ConfigLoader:
    """Load and manage configuration"""
    
    def __init__(self, config_path: Optional[str] = None):
        try:
            if config_path is None:
                base_dir = Path(__file__).parent.parent
                config_path = base_dir / 'config' / 'config.yaml'
            
            self.config_path = Path(config_path)
            if not self.config_path.exists():
                raise ConfigurationError(f"Config not found: {self.config_path}")
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            
            self._validate()
            logger.info("[OK] Configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"[ERROR] Error loading config: {e}")
            raise ConfigurationError(f"Failed to load config: {e}") from e
    
    def _validate(self):
        """Validate configuration structure"""
        required = ['trading', 'risk', 'strategies', 'api', 'logging']
        for section in required:
            if section not in self.config:
                raise ConfigurationError(f"Missing config section: {section}")
    
    def get_trading_config(self) -> Dict[str, Any]:
        """Get trading configuration"""
        return self.config.get('trading', {})
    
    def get_risk_config(self) -> Dict[str, Any]:
        """Get risk management configuration"""
        return self.config.get('risk', {})
    
    def get_strategy_config(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Get strategy configuration"""
        strategies = self.config.get('strategies', {})
        if name:
            return strategies.get(name, {})
        return strategies
    
    def get_api_config(self) -> Dict[str, Any]:
        """Get API configuration"""
        return self.config.get('api', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return self.config.get('logging', {})
    
    def get_dashboard_config(self) -> Dict[str, Any]:
        """Get dashboard configuration"""
        return self.config.get('dashboard', {})
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by key"""
        return self.config.get(key, default)


def load_config(config_path: Optional[str] = None) -> ConfigLoader:
    """Load configuration (singleton pattern)"""
    global _config_instance
    
    if _config_instance is None:
        _config_instance = ConfigLoader(config_path)
    
    return _config_instance


def get_config() -> Optional[ConfigLoader]:
    """Get current config instance"""
    global _config_instance
    return _config_instance

