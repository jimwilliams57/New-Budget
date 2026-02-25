from services.account_service import AccountService
from services.transaction_service import TransactionService
from utils.date_helpers import (
    today, current_month_str, format_month, add_months, month_range, friendly_month,
)


class NetWorthService:
    def __init__(self, account_service: AccountService, tx_service: TransactionService):
        self._acct_svc = account_service
        self._tx_svc = tx_service

    def get_current_breakdown(self) -> dict:
        """Return current net worth breakdown across all accounts."""
        accounts = self._acct_svc.get_all()
        balances = self._tx_svc.get_balances_as_of()  # all transactions, no date cap
        assets = []
        liabilities = []
        total_assets = 0.0
        total_liabilities = 0.0

        for account in accounts:
            balance = balances.get(account.id, 0.0)

            if account.is_debt_account:
                amount_owed = max(0.0, account.opening_balance - balance)
                liabilities.append({"name": account.name, "amount_owed": amount_owed})
                total_liabilities += amount_owed
            else:
                assets.append({"name": account.name, "balance": balance})
                total_assets += balance

        return {
            "assets": assets,
            "liabilities": liabilities,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "net_worth": total_assets - total_liabilities,
            "as_of_month": friendly_month(current_month_str()),
        }

    def get_monthly_history(self, months: int = 12) -> list[dict]:
        """Return net worth per month for the past `months` months, oldest first."""
        today_date = today()
        month_start = today_date.replace(day=1)

        # Build month list oldest → newest
        month_list = [
            format_month(add_months(month_start, -i))
            for i in range(months - 1, -1, -1)
        ]

        accounts = self._acct_svc.get_all()

        result = []
        for month_str in month_list:
            _, month_end = month_range(month_str)
            balances = self._tx_svc.get_balances_as_of(month_end)
            net_worth = 0.0

            for account in accounts:
                balance = balances.get(account.id, 0.0)
                if account.is_debt_account:
                    net_worth -= max(0.0, account.opening_balance - balance)
                else:
                    net_worth += balance

            result.append({"month": month_str, "net_worth": net_worth})

        return result
