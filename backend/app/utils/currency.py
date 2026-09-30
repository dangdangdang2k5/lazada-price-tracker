import re
from typing import Optional


def format_currency(amount: Optional[int]) -> str:
    """
    Format integer amount into Vietnamese currency representation.
    Example:
        1290000 -> "1.290.000đ"
        0 -> "0đ"
        None -> "N/A"
    """
    if amount is None:
        return "N/A"
    try:
        formatted = f"{amount:,}".replace(",", ".")
        return f"{formatted}đ"
    except Exception:
        return f"{amount}đ"


def parse_currency(value_str: Optional[str]) -> Optional[int]:
    """
    Parse a price string (e.g., '1.290.000 ₫', '₫ 1,290,000', '1290000', '1.290.000 VND')
    into integer.
    """
    if not value_str:
        return None
    # Remove all non-digits except possibly commas or dots
    # Extract only numeric digits
    cleaned = re.sub(r"[^\d]", "", value_str)
    if not cleaned:
        return None
    try:
        val = int(cleaned)
        return val if val > 0 else None
    except ValueError:
        return None


parseVndPrice = parse_currency
