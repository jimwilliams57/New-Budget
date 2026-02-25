from dataclasses import dataclass, field

ACCOUNT_TYPES = ("checking", "savings", "loan", "credit_card")
DEBT_ACCOUNT_TYPES = ("loan", "credit_card")

ACCOUNT_TYPE_LABELS = {
    "checking": "Checking",
    "savings": "Savings",
    "loan": "Loan",
    "credit_card": "Credit Card",
}


@dataclass
class Account:
    id: int
    name: str
    description: str = ""
    account_type: str = "checking"
    opening_balance: float = 0.0
    created_at: str = ""

    @property
    def is_debt_account(self) -> bool:
        return self.account_type in DEBT_ACCOUNT_TYPES
