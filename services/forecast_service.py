import calendar
from datetime import date


class ForecastService:
    def __init__(self, recurring_svc, budget_dao, transaction_dao):
        self._recurring_svc = recurring_svc
        self._budget_dao = budget_dao
        self._tx_dao = transaction_dao

    def _monthly_periods(self) -> list[tuple[int, int]]:
        """(year, month) tuples from this month through December of next year."""
        today = date.today()
        year, month = today.year, today.month
        end_year = today.year + 1
        periods = []
        while (year, month) <= (end_year, 12):
            periods.append((year, month))
            month += 1
            if month > 12:
                month = 1
                year += 1
        return periods

    def get_monthly_forecast(self, account_id, source: int) -> list[dict]:
        """
        [{month:'YYYY-MM', income:float, expense:float, net:float}]
        from current month through December of next year.
        source: 1=recurring only, 2=recurring+budgets, 3=recurring+history
        """
        avg_nonrecurring = None
        if source == 3:
            avg_nonrecurring = self._tx_dao.get_avg_monthly_nonrecurring(account_id, months=6)

        result = []
        for year, month in self._monthly_periods():
            month_str = f"{year}-{month:02d}"
            _, last_day = calendar.monthrange(year, month)
            month_start = date(year, month, 1)
            month_end = date(year, month, last_day)

            projected = self._recurring_svc.project_for_period(account_id, month_start, month_end)
            rec_income = sum(p["amount"] for p in projected if p["type"] == "income")
            rec_expense = sum(p["amount"] for p in projected if p["type"] == "expense")

            if source == 1:
                income = rec_income
                expense = rec_expense
            elif source == 2:
                income = rec_income
                budgets = self._budget_dao.get_by_month(month_str)
                expense = sum(b.limit_amount for b in budgets) if budgets else rec_expense
            else:  # source == 3
                income = rec_income
                expense = rec_expense + avg_nonrecurring["expense"]

            result.append({
                "month": month_str,
                "income": income,
                "expense": expense,
                "net": income - expense,
            })

        return result

    def get_annual_forecast(self, account_id, source: int) -> list[dict]:
        """
        [{year:int, income:float, expense:float, net:float}]
        for current year through current_year+9 (10 years).
        """
        today = date.today()
        monthly = self.get_monthly_forecast(account_id, source)

        # Aggregate months into years
        by_year: dict[int, dict] = {}
        for row in monthly:
            yr = int(row["month"][:4])
            if yr not in by_year:
                by_year[yr] = {"income": 0.0, "expense": 0.0}
            by_year[yr]["income"] += row["income"]
            by_year[yr]["expense"] += row["expense"]

        # Steady-state annual from last 12 months of the monthly forecast
        last_12 = monthly[-12:] if len(monthly) >= 12 else monthly
        n = max(len(last_12), 1)
        steady_income = sum(m["income"] for m in last_12) * (12 / n)
        steady_expense = sum(m["expense"] for m in last_12) * (12 / n)

        result = []
        for i in range(10):
            yr = today.year + i
            if yr in by_year:
                inc = by_year[yr]["income"]
                exp = by_year[yr]["expense"]
            else:
                inc = steady_income
                exp = steady_expense
            result.append({"year": yr, "income": inc, "expense": exp, "net": inc - exp})

        return result
