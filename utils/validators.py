"""
Input validation functions
"""
import math
from typing import Union


def validate_price(price: Union[int, float]) -> bool:
    """Validate price is positive, finite number"""
    try:
        if price is None:
            return False
        if not isinstance(price, (int, float)):
            return False
        if price <= 0:
            return False
        if math.isnan(price) or math.isinf(price):
            return False
        if price > 1000000:  # Sanity check
            return False
        return True
    except Exception:
        return False


def validate_quantity(quantity: Union[int, float]) -> bool:
    """Validate quantity is positive, finite number"""
    try:
        if quantity is None:
            return False
        if not isinstance(quantity, (int, float)):
            return False
        if quantity <= 0:
            return False
        if math.isnan(quantity) or math.isinf(quantity):
            return False
        return True
    except Exception:
        return False


def validate_percentage(value: Union[int, float], min_val: float = 0.0, max_val: float = 100.0) -> bool:
    """Validate percentage value"""
    try:
        if value is None:
            return False
        if not isinstance(value, (int, float)):
            return False
        if not (min_val <= value <= max_val):
            return False
        return True
    except Exception:
        return False


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division with fallback"""
    try:
        if denominator is None:
            return default
        if denominator == 0:
            return default
        result = numerator / denominator
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except (TypeError, ZeroDivisionError):
        return default


def safe_multiply(value1: float, value2: float, default: float = 0.0) -> float:
    """Safe multiplication with fallback"""
    try:
        if value1 is None or value2 is None:
            return default
        result = value1 * value2
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except (TypeError, ValueError):
        return default


def safe_mean(data: list, default: float = 0.0) -> float:
    """Calculate mean safely"""
    try:
        if not data or len(data) == 0:
            return default
        valid_data = [x for x in data if validate_price(x)]
        if len(valid_data) == 0:
            return default
        return sum(valid_data) / len(valid_data)
    except Exception:
        return default


def ensure_min_length(data: list, min_length: int) -> bool:
    """Check if data has minimum required length"""
    try:
        if data is None:
            return False
        if not isinstance(data, (list, tuple)):
            return False
        return len(data) >= min_length
    except Exception:
        return False


def safe_get(array: list, index: int, default=None):
    """Safely get array element"""
    try:
        if array is None:
            return default
        if not isinstance(array, (list, tuple)):
            return default
        if 0 <= index < len(array):
            return array[index]
        if -len(array) <= index < 0:
            return array[index]
        return default
    except (IndexError, TypeError):
        return default


def clamp_value(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max"""
    try:
        if value is None:
            return min_val
        if value < min_val:
            return min_val
        if value > max_val:
            return max_val
        return value
    except Exception:
        return min_val


def validate_stop_loss_take_profit(entry_price: float, stop_loss: float, take_profit: float, action: str) -> tuple:
    """Validate stop loss and take profit are correct"""
    try:
        if not all(validate_price(p) for p in [entry_price, stop_loss, take_profit]):
            return False, "Invalid price values"
        
        if action.upper() == 'BUY':
            if stop_loss >= entry_price:
                return False, "Stop loss must be < entry price for BUY"
            if take_profit <= entry_price:
                return False, "Take profit must be > entry price for BUY"
            if stop_loss >= take_profit:
                return False, "Stop loss must be < take profit for BUY"
        else:  # SELL
            if stop_loss <= entry_price:
                return False, "Stop loss must be > entry price for SELL"
            if take_profit >= entry_price:
                return False, "Take profit must be < entry price for SELL"
            if stop_loss <= take_profit:
                return False, "Stop loss must be > take profit for SELL"
        
        return True, None
        
    except Exception as e:
        return False, f"Validation error: {e}"

