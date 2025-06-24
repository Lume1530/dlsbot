from typing import List, Tuple, Any
import logging

logger = logging.getLogger(__name__)

def paginate_list(items: List[Any], page: int, page_size: int) -> Tuple[List[Any], int]:
    """Paginate a list of items"""
    if not items:
        return [], 0
    
    total_pages = (len(items) + page_size - 1) // page_size
    start = (page - 1) * page_size
    end = start + page_size
    
    return items[start:end], total_pages

def format_views(views: int) -> str:
    """Format view count for display"""
    if views >= 1_000_000_000:
        return f"{views / 1_000_000_000:.1f}B"
    elif views >= 1_000_000:
        return f"{views / 1_000_000:.1f}M"
    elif views >= 1_000:
        return f"{views / 1_000:.1f}K"
    return str(views)

def format_millions(views: int) -> str:
    """Format view count in millions/thousands"""
    if views >= 1_000_000:
        return f"{views/1_000_000:.1f}M"
    elif views >= 1_000:
        return f"{int(views/1_000)}K"
    return str(views)

def calculate_payout(views: int, rate_per_thousand: float = 0.025) -> float:
    """Calculate payout based on views"""
    return round((views / 1000) * rate_per_thousand, 2)

def calculate_tax(gross_amount: float, tax_rate: float = 0.12) -> float:
    """Calculate tax amount"""
    return round(gross_amount * tax_rate, 2)

def safe_int_conversion(value: Any, default: int = 0) -> int:
    """Safely convert value to integer"""
    try:
        if value is None:
            return default
        return int(value)
    except (ValueError, TypeError):
        logger.warning(f"Failed to convert {value} to int, using default {default}")
        return default

def safe_float_conversion(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float"""
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        logger.warning(f"Failed to convert {value} to float, using default {default}")
        return default

def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text to specified length"""
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length-1] + "…"