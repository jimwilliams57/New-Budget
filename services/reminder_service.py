from dataclasses import dataclass, field
from datetime import date, timedelta
from services.recurring_service import RecurringService
from services.budget_service import BudgetService
from utils.date_helpers import today, current_month_str, format_date, next_month
from utils.constants import UPCOMING_REMINDER_DAYS, BUDGET_ALERT_THRESHOLD


@dataclass
class Reminder:
    type: str       # 'upcoming_recurring' | 'overdue_recurring' | 'over_budget' | 'near_budget'
    severity: str   # 'info' | 'warning' | 'error'
    title: str
    detail: str
    key: str = ""   # e.g. "budget:3" or "recurring:5" — empty = not dismissable


class ReminderService:
    def __init__(
        self,
        recurring_service: RecurringService,
        budget_service: BudgetService,
    ):
        self._recurring = recurring_service
        self._budget = budget_service

    def get_reminders(
        self,
        ref_date: date | None = None,
        upcoming_days: int = UPCOMING_REMINDER_DAYS,
        threshold: float = BUDGET_ALERT_THRESHOLD,
        dismissed_keys: set[str] | None = None,
    ) -> list[Reminder]:
        ref = ref_date or today()
        reminders: list[Reminder] = []
        reminders += self._check_recurring(ref, upcoming_days)
        reminders += self._check_budgets(ref, threshold)
        order = {"error": 0, "warning": 1, "info": 2}
        sorted_reminders = sorted(reminders, key=lambda r: order[r.severity])
        if dismissed_keys:
            sorted_reminders = [r for r in sorted_reminders if r.key not in dismissed_keys]
        return sorted_reminders

    def compute_expiry(self, reminder: Reminder) -> str:
        """Return YYYY-MM-DD expiry date for a dismissed reminder.

        Budget alerts expire at the start of the next calendar month.
        Recurring reminders expire at the rule's next due date (or 30 days fallback).
        """
        today_date = today()

        if reminder.type in ("over_budget", "near_budget"):
            month_str = today_date.strftime("%Y-%m")
            next_m = next_month(month_str)
            return next_m + "-01"

        if reminder.type in ("overdue_recurring", "upcoming_recurring"):
            if reminder.key.startswith("recurring:"):
                try:
                    rule_id = int(reminder.key.split(":")[1])
                    rule = self._recurring.get_by_id(rule_id)
                    if rule:
                        next_due = self._recurring.next_due_date(rule, after=today_date)
                        if next_due:
                            return format_date(next_due)
                except (ValueError, IndexError, Exception):
                    pass

        # Fallback: 30 days from today
        return format_date(today_date + timedelta(days=30))

    def _check_recurring(self, ref: date, upcoming_days: int) -> list[Reminder]:
        reminders = []
        for rule in self._recurring.get_all():
            next_due = self._recurring.next_due_date(rule, after=ref - timedelta(days=1))
            if next_due is None:
                continue

            if next_due <= ref:
                if not rule.is_active:
                    reminders.append(Reminder(
                        type="overdue_recurring",
                        severity="warning",
                        title=f"{rule.name} is overdue",
                        detail=(
                            f"Was due on {next_due.strftime('%b %d')} · "
                            f"${rule.amount:,.2f} · {rule.category_name} · "
                            f"Rule is inactive"
                        ),
                        key=f"recurring:{rule.id}",
                    ))
            elif next_due <= ref + timedelta(days=upcoming_days):
                days_away = (next_due - ref).days
                day_label = "today" if days_away == 0 else (
                    "tomorrow" if days_away == 1 else f"in {days_away} days"
                )
                reminders.append(Reminder(
                    type="upcoming_recurring",
                    severity="info",
                    title=f"{rule.name} due {day_label}",
                    detail=(
                        f"Due on {next_due.strftime('%b %d')} · "
                        f"${rule.amount:,.2f} · {rule.category_name} · "
                        f"Account: {rule.account_name}"
                    ),
                    key=f"recurring:{rule.id}",
                ))
        return reminders

    def _check_budgets(self, ref: date, threshold: float) -> list[Reminder]:
        month = ref.strftime("%Y-%m")
        reminders = []
        for budget in self._budget.get_budget_status(month):
            if budget.limit_amount <= 0:
                continue
            pct = budget.percentage
            if pct >= 1.0:
                reminders.append(Reminder(
                    type="over_budget",
                    severity="error",
                    title=f"{budget.category_name} is over budget",
                    detail=(
                        f"Spent ${budget.spent_amount:,.2f} of "
                        f"${budget.limit_amount:,.2f} limit "
                        f"({pct*100:.0f}%)"
                    ),
                    key=f"budget:{budget.category_id}",
                ))
            elif pct >= threshold:
                reminders.append(Reminder(
                    type="near_budget",
                    severity="warning",
                    title=f"{budget.category_name} near budget limit",
                    detail=(
                        f"Spent ${budget.spent_amount:,.2f} of "
                        f"${budget.limit_amount:,.2f} limit "
                        f"({pct*100:.0f}%)"
                    ),
                    key=f"budget:{budget.category_id}",
                ))
        return reminders
