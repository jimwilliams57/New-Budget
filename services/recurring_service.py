import calendar
from datetime import date, timedelta
from models.recurring_rule import RecurringRule
from models.transaction import Transaction
from database.recurring_dao import RecurringDAO
from database.transaction_dao import TransactionDAO
from utils.date_helpers import parse_date, format_date, today
from utils.constants import RECURRING_CATCHUP_DAYS, WEEK_INTERVALS


class RecurringService:
    def __init__(self, recurring_dao: RecurringDAO, tx_dao: TransactionDAO):
        self._dao = recurring_dao
        self._tx_dao = tx_dao

    def get_all(self) -> list[RecurringRule]:
        return self._dao.get_all()

    def get_active(self) -> list[RecurringRule]:
        return self._dao.get_active()

    def get_by_id(self, rule_id: int) -> RecurringRule | None:
        return self._dao.get_by_id(rule_id)

    def create(
        self,
        name: str,
        type_: str,
        amount: float,
        account_id: int,
        category_id: int,
        description: str,
        frequency: str,
        start_date: str,
        day_of_month: int | None = None,
        day_of_week: int | None = None,
        month_of_year: int | None = None,
        end_date: str | None = None,
    ) -> RecurringRule:
        self._validate(name, type_, amount, frequency, start_date)
        return self._dao.create(
            name=name, type_=type_, amount=amount, account_id=account_id,
            category_id=category_id, description=description,
            frequency=frequency, start_date=start_date,
            day_of_month=day_of_month, day_of_week=day_of_week,
            month_of_year=month_of_year, end_date=end_date,
        )

    def update(
        self,
        rule_id: int,
        name: str,
        type_: str,
        amount: float,
        account_id: int,
        category_id: int,
        description: str,
        frequency: str,
        start_date: str,
        day_of_month: int | None = None,
        day_of_week: int | None = None,
        month_of_year: int | None = None,
        end_date: str | None = None,
        is_active: bool = True,
    ) -> RecurringRule:
        self._validate(name, type_, amount, frequency, start_date)
        return self._dao.update(
            rule_id=rule_id, name=name, type_=type_, amount=amount,
            account_id=account_id, category_id=category_id,
            description=description, frequency=frequency, start_date=start_date,
            day_of_month=day_of_month, day_of_week=day_of_week,
            month_of_year=month_of_year, end_date=end_date, is_active=is_active,
        )

    def set_active(self, rule_id: int, is_active: bool):
        self._dao.set_active(rule_id, is_active)

    def delete(self, rule_id: int):
        self._dao.delete(rule_id)

    def apply_due_rules(self, reference_date: date | None = None) -> list[Transaction]:
        """
        Apply all due recurring rules up to reference_date (default: today).
        Returns list of newly created transactions.
        """
        ref = reference_date or today()
        cutoff = ref - timedelta(days=RECURRING_CATCHUP_DAYS)
        new_transactions: list[Transaction] = []

        for rule in self._dao.get_active():
            start = parse_date(rule.start_date)
            end = parse_date(rule.end_date) if rule.end_date else None
            last = parse_date(rule.last_applied) if rule.last_applied else None

            # Determine search window start
            window_start = max(start, cutoff)
            if last:
                window_start = max(window_start, last + timedelta(days=1))

            if window_start > ref:
                continue

            # Generate all due dates in [window_start, ref]
            due_dates = self._get_due_dates(rule, window_start, ref)
            if end:
                due_dates = [d for d in due_dates if d <= end]

            for d in due_dates:
                tx = self._tx_dao.create(
                    account_id=rule.account_id,
                    type_=rule.type,
                    amount=rule.amount,
                    date=format_date(d),
                    description=rule.description,
                    category_id=rule.category_id,
                    cleared=False,
                    recurring_rule_id=rule.id,
                )
                new_transactions.append(tx)

            if due_dates:
                self._dao.update_last_applied(rule.id, format_date(due_dates[-1]))

        return new_transactions

    def next_due_date(self, rule: RecurringRule, after: date | None = None) -> date | None:
        """Return the next date the rule is due after `after` (default: today)."""
        ref = after or today()
        last = parse_date(rule.last_applied) if rule.last_applied else None
        start = parse_date(rule.start_date)
        end = parse_date(rule.end_date) if rule.end_date else None

        search_from = max(start, ref + timedelta(days=1))
        if last:
            search_from = max(search_from, last + timedelta(days=1))

        if rule.frequency in WEEK_INTERVALS:
            interval = WEEK_INTERVALS[rule.frequency]
            target_dow = rule.day_of_week if rule.day_of_week is not None else start.weekday()
            days_to_anchor = (target_dow - start.weekday()) % 7
            anchor = start + timedelta(days=days_to_anchor)
            candidate = self._first_nweekly_on_or_after(anchor, interval, search_from)
        elif rule.frequency == "monthly":
            target_day = rule.day_of_month or start.day
            candidate = self._first_monthly_on_or_after(target_day, search_from)
        elif rule.frequency == "yearly":
            target_month = rule.month_of_year or start.month
            target_day = rule.day_of_month or start.day
            candidate = self._first_yearly_on_or_after(target_month, target_day, search_from)
        else:
            return None

        if end and candidate > end:
            return None
        return candidate

    def project_for_period(
        self, account_id, start_date: date, end_date: date
    ) -> list[dict]:
        """
        Return [{date, amount, type}] for all active rules whose due dates
        fall within [start_date, end_date].  Pass account_id=None for all accounts.
        """
        result = []
        for rule in self._dao.get_active():
            if account_id is not None and rule.account_id != account_id:
                continue
            rule_start = parse_date(rule.start_date)
            rule_end = parse_date(rule.end_date) if rule.end_date else None
            if rule_end and rule_end < start_date:
                continue
            period_start = max(rule_start, start_date)
            period_end = min(rule_end, end_date) if rule_end else end_date
            if period_start > period_end:
                continue
            for d in self._get_due_dates(rule, period_start, period_end):
                result.append({"date": d, "amount": rule.amount, "type": rule.type})
        return result

    def _get_due_dates(
        self, rule: RecurringRule, start: date, end: date
    ) -> list[date]:
        result = []
        rule_start = parse_date(rule.start_date)

        if rule.frequency in WEEK_INTERVALS:
            interval = WEEK_INTERVALS[rule.frequency]
            target_dow = rule.day_of_week if rule.day_of_week is not None else rule_start.weekday()
            days_to_anchor = (target_dow - rule_start.weekday()) % 7
            anchor = rule_start + timedelta(days=days_to_anchor)
            current = self._first_nweekly_on_or_after(anchor, interval, start)
            while current <= end:
                if current >= rule_start:
                    result.append(current)
                current += timedelta(days=interval)

        elif rule.frequency == "monthly":
            target_day = rule.day_of_month or rule_start.day
            current = self._first_monthly_on_or_after(target_day, start)
            while current <= end:
                if current >= rule_start:
                    result.append(current)
                current = self._advance_one_month(current, target_day)

        elif rule.frequency == "yearly":
            target_month = rule.month_of_year or rule_start.month
            target_day = rule.day_of_month or rule_start.day
            current = self._first_yearly_on_or_after(target_month, target_day, start)
            while current <= end:
                if current >= rule_start:
                    result.append(current)
                y = current.year + 1
                current = date(y, target_month, self._resolve_dom(target_day, y, target_month))

        return result

    def _resolve_dom(self, target_day: int, y: int, m: int) -> int:
        """Resolve a day_of_month value to an actual calendar day.
        target_day == 0 means last day of month; otherwise clamped to month length."""
        last = calendar.monthrange(y, m)[1]
        return last if target_day == 0 else min(target_day, last)

    def _first_nweekly_on_or_after(self, anchor: date, interval: int, from_date: date) -> date:
        """Return the first date in the anchor + k*interval series that is >= from_date."""
        if from_date <= anchor:
            return anchor
        days_since = (from_date - anchor).days
        n = days_since // interval
        candidate = anchor + timedelta(days=n * interval)
        if candidate < from_date:
            candidate += timedelta(days=interval)
        return candidate

    def _first_monthly_on_or_after(self, target_day: int, from_date: date) -> date:
        y, m = from_date.year, from_date.month
        effective = self._resolve_dom(target_day, y, m)
        if effective >= from_date.day:
            return date(y, m, effective)
        m += 1
        if m > 12:
            y, m = y + 1, 1
        return date(y, m, self._resolve_dom(target_day, y, m))

    def _advance_one_month(self, d: date, target_day: int) -> date:
        y, m = d.year, d.month + 1
        if m > 12:
            y, m = y + 1, 1
        return date(y, m, self._resolve_dom(target_day, y, m))

    def _first_yearly_on_or_after(self, target_month: int, target_day: int, from_date: date) -> date:
        y = from_date.year
        effective = self._resolve_dom(target_day, y, target_month)
        candidate = date(y, target_month, effective)
        if candidate < from_date:
            y += 1
            candidate = date(y, target_month, self._resolve_dom(target_day, y, target_month))
        return candidate

    def _is_due_on(self, rule: RecurringRule, d: date) -> bool:
        start = parse_date(rule.start_date)
        if d < start:
            return False

        if rule.frequency == "monthly":
            target_day = rule.day_of_month or start.day
            return d.day == self._resolve_dom(target_day, d.year, d.month)

        elif rule.frequency in WEEK_INTERVALS:
            interval = WEEK_INTERVALS[rule.frequency]
            target_dow = rule.day_of_week if rule.day_of_week is not None else start.weekday()
            if d.weekday() != target_dow:
                return False
            days_to_anchor = (target_dow - start.weekday()) % 7
            anchor = start + timedelta(days=days_to_anchor)
            return (d - anchor).days % interval == 0

        elif rule.frequency == "yearly":
            target_month = rule.month_of_year or start.month
            target_day = rule.day_of_month or start.day
            if d.month != target_month:
                return False
            return d.day == self._resolve_dom(target_day, d.year, d.month)

        return False

    def _validate(self, name, type_, amount, frequency, start_date):
        if not name.strip():
            raise ValueError("Name cannot be empty.")
        if type_ not in ("income", "expense"):
            raise ValueError("Type must be income or expense.")
        if amount <= 0:
            raise ValueError("Amount must be positive.")
        if frequency not in ("monthly", "yearly") and frequency not in WEEK_INTERVALS:
            raise ValueError("Invalid frequency.")
        if not parse_date(start_date):
            raise ValueError("Invalid start date.")
