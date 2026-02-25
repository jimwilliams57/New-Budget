from models.account import Account, ACCOUNT_TYPES, DEBT_ACCOUNT_TYPES
from database.account_dao import AccountDAO


class AccountService:
    def __init__(self, account_dao: AccountDAO):
        self._dao = account_dao

    def get_all(self) -> list[Account]:
        return self._dao.get_all()

    def get_by_id(self, account_id: int) -> Account | None:
        return self._dao.get_by_id(account_id)

    def create(
        self,
        name: str,
        description: str = "",
        account_type: str = "checking",
        opening_balance: float = 0.0,
    ) -> Account:
        name = name.strip()
        if not name:
            raise ValueError("Account name cannot be empty.")
        if self._dao.get_by_name(name):
            raise ValueError(f"An account named '{name}' already exists.")
        self._validate_type(account_type)
        opening_balance = self._sanitize_opening_balance(account_type, opening_balance)
        return self._dao.create(name, description.strip(), account_type, opening_balance)

    def update(
        self,
        account_id: int,
        name: str,
        description: str = "",
        account_type: str = "checking",
        opening_balance: float = 0.0,
    ) -> Account:
        name = name.strip()
        if not name:
            raise ValueError("Account name cannot be empty.")
        existing = self._dao.get_by_name(name)
        if existing and existing.id != account_id:
            raise ValueError(f"An account named '{name}' already exists.")
        self._validate_type(account_type)
        # Guard: cannot change account type if transactions exist
        current = self._dao.get_by_id(account_id)
        if current and current.account_type != account_type:
            if self._dao.has_transactions(account_id):
                raise ValueError(
                    "Cannot change account type when the account has existing transactions."
                )
        opening_balance = self._sanitize_opening_balance(account_type, opening_balance)
        return self._dao.update(account_id, name, description.strip(), account_type, opening_balance)

    def delete(self, account_id: int):
        if self._dao.has_transactions(account_id):
            raise ValueError(
                "Cannot delete an account with existing transactions. "
                "Remove all transactions first."
            )
        self._dao.delete(account_id)

    def get_names(self) -> list[str]:
        return [a.name for a in self._dao.get_all()]

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _validate_type(account_type: str):
        if account_type not in ACCOUNT_TYPES:
            raise ValueError(
                f"Invalid account type '{account_type}'. "
                f"Must be one of: {', '.join(ACCOUNT_TYPES)}."
            )

    @staticmethod
    def _sanitize_opening_balance(account_type: str, opening_balance: float) -> float:
        if account_type not in DEBT_ACCOUNT_TYPES:
            return 0.0
        if opening_balance < 0:
            raise ValueError("Opening balance must be 0 or greater.")
        return opening_balance
