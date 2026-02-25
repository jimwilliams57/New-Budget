from dataclasses import dataclass
from typing import Optional


@dataclass
class RecurringRule:
    id: int
    name: str
    type: str               # 'income' | 'expense'
    amount: float
    account_id: int
    category_id: int
    description: str
    frequency: str          # 'monthly' | 'weekly' | 'yearly'
    start_date: str         # 'YYYY-MM-DD'
    is_active: bool
    day_of_month: Optional[int] = None   # 1-28, or 0 = last day of month
    day_of_week: Optional[int] = None    # 0=Mon..6=Sun
    month_of_year: Optional[int] = None  # 1-12
    end_date: Optional[str] = None
    last_applied: Optional[str] = None
    account_name: str = ""
    category_name: str = ""
