"""
Custom exception classes for trading bot
"""


class TradingBotError(Exception):
    """Base exception for all bot errors"""
    pass


class APIError(TradingBotError):
    """API-related errors"""
    pass


class RiskManagementError(TradingBotError):
    """Risk management errors"""
    pass


class ConfigurationError(TradingBotError):
    """Configuration errors"""
    pass


class DataError(TradingBotError):
    """Data-related errors"""
    pass


class StrategyError(TradingBotError):
    """Strategy errors"""
    pass

