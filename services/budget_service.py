from models.budget import Budget
from database.budget_dao import BudgetDAO
from database.transaction_dao import TransactionDAO
from database.category_dao import CategoryDAO
from utils.date_helpers import current_month_str


class BudgetService:
    def __init__(
        self,
        budget_dao: BudgetDAO,
        tx_dao: TransactionDAO,
        category_dao: CategoryDAO,
    ):
        self._budget_dao = budget_dao
        self._tx_dao = tx_dao
        self._category_dao = category_dao

    def get_budget_status(self, month: str | None = None) -> list[Budget]:
        """Return all budgets for the month with spent amounts filled in."""
        if month is None:
            month = current_month_str()
        budgets = self._budget_dao.get_by_month(month)
        spending = self._tx_dao.get_spending_by_category(month)
        for b in budgets:
            b.spent_amount = spending.get(b.category_id, 0.0)
        return budgets

    def upsert(self, category_id: int, month: str, limit_amount: float) -> Budget:
        if limit_amount < 0:
            raise ValueError("Budget limit must be non-negative.")
        return self._budget_dao.upsert(category_id, month, limit_amount)

    def delete(self, budget_id: int):
        self._budget_dao.delete(budget_id)

    def copy_from_previous_month(self, to_month: str) -> int:
        from utils.date_helpers import prev_month
        from_month = prev_month(to_month)
        return self._budget_dao.copy_month(from_month, to_month)

    def get_expense_categories(self):
        """Return categories valid for budgeting (expense or both)."""
        return [
            c for c in self._category_dao.get_all()
            if c.type in ("expense", "both")
        ]
