from models.transaction import Transaction
from database.transaction_dao import TransactionDAO
from database.account_dao import AccountDAO
from utils.date_helpers import parse_date


class TransactionService:
    def __init__(self, tx_dao: TransactionDAO, account_dao: AccountDAO):
        self._dao = tx_dao
        self._account_dao = account_dao

    def get_for_account(
        self,
        account_id: int,
        month: str | None = None,
        type_filter: str | None = None,
        cleared_filter: str | None = None,
        search: str | None = None,
    ) -> list[Transaction]:
        return self._dao.get_by_account(
            account_id, month, type_filter, cleared_filter, search
        )

    def get_with_running_balance(
        self,
        account_id: int,
        month: str | None = None,
        type_filter: str | None = None,
        cleared_filter: str | None = None,
        search: str | None = None,
    ) -> list[tuple[Transaction, float]]:
        """Returns transactions paired with running balance for display."""
        # Always get ALL transactions for balance calculation
        all_tx = self._dao.get_by_account(account_id)
        filtered = self._dao.get_by_account(
            account_id, month, type_filter, cleared_filter, search
        )

        # Pre-fetch all transfer pairs in a single batch query
        transfer_pair_ids = list({
            tx.transfer_pair_id for tx in all_tx
            if tx.type == "transfer" and tx.transfer_pair_id is not None
        })
        pair_map = self._dao.get_by_transfer_pair_ids(transfer_pair_ids)

        # Build running balance map: tx.id → cumulative balance
        balance = 0.0
        balance_map: dict[int, float] = {}
        for tx in all_tx:
            if tx.type == "income":
                balance += tx.amount
            elif tx.type == "expense":
                balance -= tx.amount
            elif tx.type == "transfer":
                # Debit side: negative; credit side: positive
                # Convention: the row with the lower id is the debit (from-account)
                if tx.transfer_pair_id:
                    pair = pair_map.get(tx.transfer_pair_id, [])
                    if len(pair) == 2:
                        debit_id = min(p.id for p in pair)
                        if tx.id == debit_id:
                            balance -= tx.amount
                        else:
                            balance += tx.amount
                    else:
                        balance -= tx.amount
                else:
                    balance -= tx.amount
            balance_map[tx.id] = balance

        return [(tx, balance_map.get(tx.id, 0.0)) for tx in filtered]

    def get_balances_as_of(self, as_of_date: str | None = None) -> dict[int, float]:
        """Return {account_id: balance} for all accounts via a single SQL aggregate.
        as_of_date is YYYY-MM-DD; omit to include all transactions."""
        return self._dao.get_balances_as_of(as_of_date)

    def get_totals(self, account_id: int, month: str) -> dict:
        totals = self._dao.get_totals_by_account(account_id, month)
        totals["net"] = totals["income"] - totals["expense"]
        return totals

    def create_income_expense(
        self,
        account_id: int,
        type_: str,
        amount: float,
        date: str,
        category_id: int,
        description: str = "",
        cleared: bool = False,
        recurring_rule_id: int | None = None,
    ) -> Transaction:
        self._validate(type_, amount, date)
        return self._dao.create(
            account_id=account_id,
            type_=type_,
            amount=amount,
            date=date,
            description=description,
            category_id=category_id,
            cleared=cleared,
            recurring_rule_id=recurring_rule_id,
        )

    def create_transfer(
        self,
        from_account_id: int,
        to_account_id: int,
        amount: float,
        date: str,
        description: str = "",
    ) -> tuple[Transaction, Transaction]:
        """Atomically create both sides of a transfer."""
        if from_account_id == to_account_id:
            raise ValueError("Cannot transfer to the same account.")
        if amount <= 0:
            raise ValueError("Amount must be positive.")
        if not parse_date(date):
            raise ValueError("Invalid date.")

        conn = self._dao._db.get_connection()
        try:
            pair_id = self._dao.get_next_transfer_pair_id()
            debit = self._dao.create(
                account_id=from_account_id,
                type_="transfer",
                amount=amount,
                date=date,
                description=description,
                category_id=None,
                cleared=False,
                transfer_pair_id=pair_id,
            )
            credit = self._dao.create(
                account_id=to_account_id,
                type_="transfer",
                amount=amount,
                date=date,
                description=description,
                category_id=None,
                cleared=False,
                transfer_pair_id=pair_id,
            )
            conn.commit()
            return debit, credit
        except Exception:
            conn.rollback()
            raise

    def update(
        self,
        tx_id: int,
        type_: str,
        amount: float,
        date: str,
        category_id: int | None,
        description: str = "",
        cleared: bool = False,
    ) -> Transaction:
        self._validate(type_, amount, date)
        return self._dao.update(
            tx_id, type_, amount, date, description, category_id, cleared
        )

    def set_cleared(self, tx_id: int, cleared: bool):
        self._dao.set_cleared(tx_id, cleared)

    def delete(self, tx_id: int):
        self._dao.delete(tx_id)

    def delete_transfer_pair(self, pair_id: int):
        self._dao.delete_by_transfer_pair(pair_id)

    def get_transfer_pair(self, pair_id: int) -> list[Transaction]:
        return self._dao.get_by_transfer_pair(pair_id)

    def _validate(self, type_: str, amount: float, date: str):
        if type_ not in ("income", "expense", "transfer"):
            raise ValueError(f"Invalid type: {type_}")
        if amount <= 0:
            raise ValueError("Amount must be positive.")
        if not parse_date(date):
            raise ValueError("Invalid date format. Use YYYY-MM-DD.")
