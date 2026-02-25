def format_currency(amount: float, symbol: str = "$") -> str:
    """Format a float as currency string, e.g. '$1,234.56'."""
    return f"{symbol}{amount:,.2f}"


def format_signed(amount: float, symbol: str = "$") -> str:
    """Format with +/- sign."""
    sign = "+" if amount >= 0 else "-"
    return f"{sign}{symbol}{abs(amount):,.2f}"
