from database.transaction_dao import TransactionDAO
from database.account_dao import AccountDAO
from utils.date_helpers import current_month_str


class ReportService:
    def __init__(self, tx_dao: TransactionDAO, account_dao: AccountDAO):
        self._tx_dao = tx_dao
        self._account_dao = account_dao

    def get_monthly_chart_data(
        self, account_id: int | None = None, months: int = 6
    ) -> list[dict]:
        """Return list of {month, income, expense, net} for bar chart."""
        rows = self._tx_dao.get_monthly_totals(account_id, months)
        for row in rows:
            row["net"] = row.get("income", 0) - row.get("expense", 0)
        return rows

    def get_category_breakdown(
        self, month: str | None = None, account_id: int | None = None
    ) -> list[dict]:
        """Return [{category, color_hex, total}, ...] for pie chart."""
        m = month or current_month_str()
        return self._tx_dao.get_expense_by_category(m, account_id)

    def get_summary(
        self, month: str | None = None, account_id: int | None = None
    ) -> dict:
        m = month or current_month_str()
        if account_id:
            totals = self._tx_dao.get_totals_by_account(account_id, m)
        else:
            totals = self._tx_dao.get_totals_for_month(m)
        totals["net"] = totals["income"] - totals["expense"]
        return totals

    def export_csv(
        self, account_id: int | None, month: str | None = None
    ) -> list[list[str]]:
        """Return rows suitable for CSV export."""
        from utils.date_helpers import current_month_str
        m = month or current_month_str()
        all_accounts = self._account_dao.get_all()
        if account_id:
            transactions = self._tx_dao.get_by_account(account_id, month=m)
        else:
            transactions = []
            for acct in all_accounts:
                transactions.extend(
                    self._tx_dao.get_by_account(acct.id, month=m)
                )
            transactions.sort(key=lambda t: (t.date, t.id))

        header = ["Date", "Type", "Category", "Description", "Amount", "Cleared", "Account"]
        rows = [header]
        account_map = {a.id: a.name for a in all_accounts}
        for tx in transactions:
            rows.append([
                tx.date,
                tx.type,
                tx.category_name or "",
                tx.description,
                f"{tx.amount:.2f}",
                "Yes" if tx.cleared else "No",
                account_map.get(tx.account_id, ""),
            ])
        return rows
