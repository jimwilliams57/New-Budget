import os
import sys
import customtkinter as ctk

# Ensure project root is on sys.path when run directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager
from database.account_dao import AccountDAO
from database.transaction_dao import TransactionDAO
from database.category_dao import CategoryDAO
from database.budget_dao import BudgetDAO
from database.recurring_dao import RecurringDAO
from database.dismissed_reminder_dao import DismissedReminderDAO

from services.account_service import AccountService
from services.transaction_service import TransactionService
from services.budget_service import BudgetService
from services.recurring_service import RecurringService
from services.report_service import ReportService
from services.reminder_service import ReminderService
from services.forecast_service import ForecastService
from services.net_worth_service import NetWorthService
from services.category_service import CategoryService
from services.data_service import DataService

from ui.app_window import AppWindow
from utils.app_config import get_db_folder
from utils.constants import APP_NAME
from utils.date_helpers import format_date, today


def main():
    # ── Bootstrap: read DB folder from pre-DB config ──────────────────────────
    db_folder = get_db_folder()

    # ── Database ─────────────────────────────────────────────────────────────
    db = DatabaseManager.open_for_current_year(db_folder=db_folder)

    # ── DAOs ─────────────────────────────────────────────────────────────────
    account_dao = AccountDAO(db)
    tx_dao = TransactionDAO(db)
    category_dao = CategoryDAO(db)
    budget_dao = BudgetDAO(db)
    recurring_dao = RecurringDAO(db)
    dismissed_reminder_dao = DismissedReminderDAO(db)

    # ── Services ─────────────────────────────────────────────────────────────
    account_svc = AccountService(account_dao)
    tx_svc = TransactionService(tx_dao, account_dao)
    budget_svc = BudgetService(budget_dao, tx_dao, category_dao)
    recurring_svc = RecurringService(recurring_dao, tx_dao)
    report_svc = ReportService(tx_dao, account_dao)
    reminder_svc = ReminderService(recurring_svc, budget_svc)
    forecast_svc = ForecastService(recurring_svc, budget_dao, tx_dao)
    net_worth_svc = NetWorthService(account_svc, tx_svc)
    category_svc = CategoryService(category_dao)
    data_svc = DataService(db, account_dao, category_dao, budget_dao, recurring_dao, tx_dao, tx_svc)

    # ── Apply due recurring rules ────────────────────────────────────────────
    new_transactions = recurring_svc.apply_due_rules()

    # ── Filter dismissed reminders, then gather startup reminders ─────────────
    ref_date_str = format_date(today())
    dismissed_keys = dismissed_reminder_dao.get_active_keys(ref_date_str)
    reminders = reminder_svc.get_reminders(dismissed_keys=dismissed_keys)

    # ── Restore last-used account ─────────────────────────────────────────────
    last_account_id_str = db.get_setting("last_account_id", "")
    initial_account = None
    if last_account_id_str:
        try:
            initial_account = account_dao.get_by_id(int(last_account_id_str))
        except (ValueError, Exception):
            pass

    # ── Appearance ───────────────────────────────────────────────────────────
    appearance = db.get_setting("appearance_mode", "system")
    date_format = db.get_setting("date_format", "MM/DD/YYYY")
    ctk.set_appearance_mode(appearance)
    ctk.set_default_color_theme("blue")

    # ── Launch UI ────────────────────────────────────────────────────────────
    app = AppWindow(
        account_service=account_svc,
        tx_service=tx_svc,
        budget_service=budget_svc,
        recurring_service=recurring_svc,
        report_service=report_svc,
        reminder_service=reminder_svc,
        forecast_service=forecast_svc,
        net_worth_service=net_worth_svc,
        category_service=category_svc,
        category_dao=category_dao,
        db=db,
        data_service=data_svc,
        dismissed_reminder_dao=dismissed_reminder_dao,
        initial_account=initial_account,
        startup_reminders=reminders,
        startup_transactions=new_transactions,
        date_format=date_format,
    )

    # Save last-used account on close
    def on_close():
        if app._current_account:
            db.set_setting("last_account_id", str(app._current_account.id))
        db.close()
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", on_close)
    app.mainloop()


if __name__ == "__main__":
    main()
