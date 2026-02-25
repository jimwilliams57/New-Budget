from dataclasses import dataclass
from typing import Optional


@dataclass
class Transaction:
    id: int
    account_id: int
    type: str               # 'income' | 'expense' | 'transfer'
    amount: float
    category_id: Optional[int]
    category_name: str
    description: str
    date: str               # 'YYYY-MM-DD'
    cleared: bool
    transfer_pair_id: Optional[int] = None
    recurring_rule_id: Optional[int] = None
    created_at: str = ""
    updated_at: str = ""
