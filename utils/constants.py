APP_NAME = "New Budget"
APP_WIDTH = 1200
APP_HEIGHT = 750
DB_FILE = "budget.db"


def db_file_for_year(year: int) -> str:
    return f"budget_{year}.db"
DEFAULT_ACCOUNT_NAME = "Checking"
DATE_FORMAT = "%Y-%m-%d"
MONTH_FORMAT = "%Y-%m"
BUDGET_ALERT_THRESHOLD = 0.80  # default 80%
RECURRING_CATCHUP_DAYS = 90
UPCOMING_REMINDER_DAYS = 7

DEFAULT_CATEGORIES = [
    {"name": "Salary",         "type": "income",   "color_hex": "#4CAF50", "is_system": 1},
    {"name": "Freelance",      "type": "income",   "color_hex": "#8BC34A", "is_system": 1},
    {"name": "Food & Dining",  "type": "expense",  "color_hex": "#FF9800", "is_system": 1},
    {"name": "Rent/Mortgage",  "type": "expense",  "color_hex": "#F44336", "is_system": 1},
    {"name": "Utilities",      "type": "expense",  "color_hex": "#9C27B0", "is_system": 1},
    {"name": "Transport",      "type": "expense",  "color_hex": "#2196F3", "is_system": 1},
    {"name": "Healthcare",     "type": "expense",  "color_hex": "#00BCD4", "is_system": 1},
    {"name": "Entertainment",  "type": "expense",  "color_hex": "#FF5722", "is_system": 1},
    {"name": "Savings",        "type": "both",     "color_hex": "#009688", "is_system": 1},
    {"name": "Other",          "type": "both",     "color_hex": "#888888", "is_system": 1},
]

SEVERITY_COLORS = {
    "error":   "#F44336",
    "warning": "#FF9800",
    "info":    "#2196F3",
}

SEVERITY_ICONS = {
    "error":   "❗",
    "warning": "⚠",
    "info":    "ℹ",
}

TRANSACTION_TYPES = ["income", "expense", "transfer"]
FREQUENCIES = ["monthly", "weekly", "every 2 weeks", "every 3 weeks", "every 4 weeks", "yearly"]
DAYS_OF_WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WEEK_INTERVALS = {
    "weekly": 7,
    "every 2 weeks": 14,
    "every 3 weeks": 21,
    "every 4 weeks": 28,
}
