from datetime import date, datetime, timedelta
import calendar
from utils.constants import DATE_FORMAT, MONTH_FORMAT

# ── Display date format options ───────────────────────────────────────────────

DATE_FORMAT_OPTIONS = ["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD", "DD.MM.YYYY", "MM-DD-YYYY"]

_STRFTIME_MAP = {
    "MM/DD/YYYY": "%m/%d/%Y",
    "DD/MM/YYYY": "%d/%m/%Y",
    "YYYY-MM-DD": "%Y-%m-%d",
    "DD.MM.YYYY": "%d.%m.%Y",
    "MM-DD-YYYY": "%m-%d-%Y",
}

_TKCAL_MAP = {
    "MM/DD/YYYY": "mm/dd/yyyy",
    "DD/MM/YYYY": "dd/mm/yyyy",
    "YYYY-MM-DD": "yyyy-mm-dd",
    "DD.MM.YYYY": "dd.mm.yyyy",
    "MM-DD-YYYY": "mm-dd-yyyy",
}


def today() -> date:
    return date.today()


def today_str() -> str:
    return date.today().strftime(DATE_FORMAT)


def current_month_str() -> str:
    return date.today().strftime(MONTH_FORMAT)


def parse_date(date_str: str) -> date | None:
    """Parse a date string in YYYY-MM-DD format, returning None on failure."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def format_date(d: date) -> str:
    return d.strftime(DATE_FORMAT)


def format_month(d: date) -> str:
    return d.strftime(MONTH_FORMAT)


def parse_month(month_str: str) -> date | None:
    """Return the first day of the given YYYY-MM month string."""
    if not month_str:
        return None
    try:
        return datetime.strptime(month_str, MONTH_FORMAT).date()
    except ValueError:
        return None


def month_range(month_str: str) -> tuple[str, str]:
    """Return (first_day_str, last_day_str) for a YYYY-MM month."""
    d = parse_month(month_str)
    if d is None:
        raise ValueError(f"Invalid month: {month_str}")
    last_day = calendar.monthrange(d.year, d.month)[1]
    return (
        format_date(d),
        format_date(d.replace(day=last_day)),
    )


def prev_month(month_str: str) -> str:
    d = parse_month(month_str)
    if d is None:
        raise ValueError(f"Invalid month: {month_str}")
    if d.month == 1:
        return format_month(d.replace(year=d.year - 1, month=12))
    return format_month(d.replace(month=d.month - 1))


def next_month(month_str: str) -> str:
    d = parse_month(month_str)
    if d is None:
        raise ValueError(f"Invalid month: {month_str}")
    if d.month == 12:
        return format_month(d.replace(year=d.year + 1, month=1))
    return format_month(d.replace(month=d.month + 1))


def clamp_day_to_month(year: int, month: int, day: int) -> int:
    """Clamp day to valid range for the given year/month."""
    max_day = calendar.monthrange(year, month)[1]
    return min(day, max_day)


def add_months(d: date, n: int) -> date:
    """Add n months to date d, clamping day to month end."""
    month = d.month - 1 + n
    year = d.year + month // 12
    month = month % 12 + 1
    day = clamp_day_to_month(year, month, d.day)
    return d.replace(year=year, month=month, day=day)


def friendly_month(month_str: str) -> str:
    """Convert YYYY-MM to e.g. 'February 2026'."""
    d = parse_month(month_str)
    if d is None:
        return month_str
    return d.strftime("%B %Y")


def format_display_date(date_str: str, fmt_key: str = "MM/DD/YYYY") -> str:
    """Convert a YYYY-MM-DD storage string to the user-facing display format."""
    if not date_str:
        return date_str
    d = parse_date(date_str)
    if d is None:
        return date_str
    return d.strftime(_STRFTIME_MAP.get(fmt_key, "%m/%d/%Y"))


def tkcal_date_pattern(fmt_key: str) -> str:
    """Return the tkcalendar date_pattern string for the given format key."""
    return _TKCAL_MAP.get(fmt_key, "mm/dd/yyyy")


def parse_display_date(display_str: str, fmt_key: str) -> date | None:
    """Parse a date in the given display format. Returns None on failure.

    Falls back to ISO 8601 parse if the display format doesn't match.
    """
    if not display_str:
        return None
    fmt = _STRFTIME_MAP.get(fmt_key, "%m/%d/%Y")
    try:
        return datetime.strptime(display_str.strip(), fmt).date()
    except ValueError:
        return parse_date(display_str)
