import customtkinter as ctk
from models.account import Account, ACCOUNT_TYPE_LABELS
from models.transaction import Transaction
from services.account_service import AccountService
from services.transaction_service import TransactionService
from services.budget_service import BudgetService
from services.recurring_service import RecurringService
from services.report_service import ReportService
from services.reminder_service import Reminder, ReminderService
from services.forecast_service import ForecastService
from services.net_worth_service import NetWorthService
from services.category_service import CategoryService
from services.data_service import DataService
from database.category_dao import CategoryDAO
from database.db_manager import DatabaseManager
from ui.components.account_form import AccountForm
from ui.components.alert_banner import AlertBanner
from ui.components.reminder_dialog import ReminderDialog
from ui.tabs.dashboard_tab import DashboardTab
from ui.tabs.register_tab import RegisterTab
from ui.tabs.budgets_tab import BudgetsTab
from ui.tabs.reports_tab import ReportsTab
from ui.tabs.recurring_tab import RecurringTab
from ui.tabs.forecast_tab import ForecastTab
from ui.tabs.net_worth_tab import NetWorthTab
from ui.tabs.categories_tab import CategoriesTab
from ui.tabs.settings_tab import SettingsTab
from utils.constants import APP_NAME, APP_WIDTH, APP_HEIGHT


_REFRESH_SCOPES: dict[str, set[str]] = {
    "transaction": {"dashboard", "register", "budgets", "reports", "net_worth", "forecast"},
    "budget":      {"dashboard", "budgets"},
    "recurring":   {"dashboard", "recurring", "forecast"},
    "category":    {"dashboard", "register", "budgets", "reports", "categories"},
    "account":     {"dashboard", "register", "reports", "net_worth", "forecast"},
    "full":        {"dashboard", "register", "budgets", "recurring", "reports",
                    "net_worth", "forecast", "categories", "settings"},
}


class AppWindow(ctk.CTk):
    def __init__(
        self,
        account_service: AccountService,
        tx_service: TransactionService,
        budget_service: BudgetService,
        recurring_service: RecurringService,
        report_service: ReportService,
        reminder_service: ReminderService,
        forecast_service: ForecastService,
        net_worth_service: NetWorthService,
        category_service: CategoryService,
        category_dao: CategoryDAO,
        db: DatabaseManager | None = None,
        data_service: DataService | None = None,
        dismissed_reminder_dao=None,
        initial_account: Account | None = None,
        startup_reminders: list[Reminder] | None = None,
        startup_transactions: list[Transaction] | None = None,
        date_format: str = "MM/DD/YYYY",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._acct_svc = account_service
        self._tx_svc = tx_service
        self._budget_svc = budget_service
        self._recurring_svc = recurring_service
        self._report_svc = report_service
        self._reminder_svc = reminder_service
        self._forecast_svc = forecast_service
        self._net_worth_svc = net_worth_service
        self._cat_svc = category_service
        self._cat_dao = category_dao
        self._db = db
        self._data_svc = data_service
        self._dismissed_dao = dismissed_reminder_dao
        self._startup_reminders = startup_reminders or []
        self._startup_transactions = startup_transactions or []
        self._date_format = date_format

        self.title(APP_NAME)
        self.minsize(APP_WIDTH, APP_HEIGHT)
        self.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")

        self._accounts = self._acct_svc.get_all()
        self._current_account: Account | None = (
            initial_account or (self._accounts[0] if self._accounts else None)
        )

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_account_bar()
        self._build_banner_area()
        self._build_tabs()

        # Show startup banner for new recurring transactions
        if self._startup_transactions:
            count = len(self._startup_transactions)
            self.after(300, lambda: self._show_recurring_banner(count))

        # Show reminder dialog after window is drawn
        if self._startup_reminders:
            self.after(200, self._show_reminder_dialog)

    # ── Account bar ─────────────────────────────────────────────────────────
    def _build_account_bar(self):
        bar = ctk.CTkFrame(self, fg_color=("gray85", "gray15"), corner_radius=0, height=44)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(bar, text="Account:", anchor="e").pack(side="left", padx=(12, 4), pady=8)

        account_names = [a.name for a in self._accounts]
        current_name = self._current_account.name if self._current_account else ""
        self._acct_combo_var = ctk.StringVar(value=current_name)
        self._acct_combo = ctk.CTkComboBox(
            bar,
            values=account_names,
            variable=self._acct_combo_var,
            width=200,
            state="readonly",
            command=self.on_account_changed,
        )
        self._acct_combo.pack(side="left", padx=4)

        ctk.CTkButton(
            bar, text="+ New Account", width=110,
            command=self._open_new_account,
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            bar, text="Edit Account", width=100,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"),
            command=self._open_edit_account,
        ).pack(side="left", padx=4)

        self._acct_type_label = ctk.CTkLabel(bar, text="", text_color="gray60", width=90)
        self._acct_type_label.pack(side="left", padx=(4, 8))
        self._update_acct_type_label()

    def _build_banner_area(self):
        self._banner_frame = ctk.CTkFrame(self, fg_color="transparent", height=0)
        self._banner_frame.grid(row=1, column=0, sticky="ew", padx=8)

    def _build_tabs(self):
        self._tabview = ctk.CTkTabview(self)
        self._tabview.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))

        tab_names = [
            "Dashboard", "Register", "Budgets", "Recurring",
            "Reports", "Net Worth", "Forecast", "Categories", "Settings",
        ]
        for tab_name in tab_names:
            self._tabview.add(tab_name)
            self._tabview.tab(tab_name).grid_columnconfigure(0, weight=1)
            self._tabview.tab(tab_name).grid_rowconfigure(0, weight=1)

        self._dashboard_tab = DashboardTab(
            self._tabview.tab("Dashboard"),
            tx_service=self._tx_svc,
            budget_service=self._budget_svc,
            get_account_id=self._get_current_account_id,
            get_account=lambda: self._current_account,
            date_format=self._date_format,
        )
        self._dashboard_tab.grid(row=0, column=0, sticky="nsew")

        self._register_tab = RegisterTab(
            self._tabview.tab("Register"),
            tx_service=self._tx_svc,
            account_service=self._acct_svc,
            category_dao=self._cat_dao,
            get_account_id=self._get_current_account_id,
            get_account=lambda: self._current_account,
            notify_refresh=self.notify_tabs_refresh,
            date_format=self._date_format,
        )
        self._register_tab.grid(row=0, column=0, sticky="nsew")

        self._budgets_tab = BudgetsTab(
            self._tabview.tab("Budgets"),
            budget_service=self._budget_svc,
            notify_refresh=self.notify_tabs_refresh,
        )
        self._budgets_tab.grid(row=0, column=0, sticky="nsew")

        self._reports_tab = ReportsTab(
            self._tabview.tab("Reports"),
            report_service=self._report_svc,
            account_service=self._acct_svc,
        )
        self._reports_tab.grid(row=0, column=0, sticky="nsew")

        self._net_worth_tab = NetWorthTab(
            self._tabview.tab("Net Worth"),
            net_worth_service=self._net_worth_svc,
        )
        self._net_worth_tab.grid(row=0, column=0, sticky="nsew")

        self._recurring_tab = RecurringTab(
            self._tabview.tab("Recurring"),
            recurring_service=self._recurring_svc,
            account_service=self._acct_svc,
            category_dao=self._cat_dao,
            notify_refresh=self.notify_tabs_refresh,
            date_format=self._date_format,
        )
        self._recurring_tab.grid(row=0, column=0, sticky="nsew")

        self._forecast_tab = ForecastTab(
            self._tabview.tab("Forecast"),
            forecast_service=self._forecast_svc,
            account_service=self._acct_svc,
        )
        self._forecast_tab.grid(row=0, column=0, sticky="nsew")

        self._categories_tab = CategoriesTab(
            self._tabview.tab("Categories"),
            category_service=self._cat_svc,
            notify_refresh=self.notify_tabs_refresh,
        )
        self._categories_tab.grid(row=0, column=0, sticky="nsew")

        # Settings tab (only if db and data_service provided)
        if self._db and self._data_svc:
            self._settings_tab = SettingsTab(
                self._tabview.tab("Settings"),
                db=self._db,
                data_service=self._data_svc,
                notify_refresh=self.notify_tabs_refresh,
            )
            self._settings_tab.grid(row=0, column=0, sticky="nsew")
        else:
            self._settings_tab = None

    # ── Account management ───────────────────────────────────────────────────
    def on_account_changed(self, value=None):
        name = self._acct_combo_var.get()
        self._current_account = next(
            (a for a in self._accounts if a.name == name), None
        )
        self._update_acct_type_label()
        self.notify_tabs_refresh("account")

    def _get_current_account_id(self) -> int | None:
        return self._current_account.id if self._current_account else None

    def _open_new_account(self):
        form = AccountForm(self, self._acct_svc)
        self.wait_window(form)
        if form.saved:
            self._refresh_account_bar()
            self.notify_tabs_refresh("account")

    def _open_edit_account(self):
        if not self._current_account:
            return
        form = AccountForm(
            self, self._acct_svc,
            account=self._current_account,
            on_delete_callback=self._on_account_deleted,
        )
        self.wait_window(form)
        if form.saved:
            self._refresh_account_bar()
            self.notify_tabs_refresh("account")

    def _on_account_deleted(self):
        self._current_account = None

    def _refresh_account_bar(self):
        self._accounts = self._acct_svc.get_all()
        names = [a.name for a in self._accounts]
        self._acct_combo.configure(values=names)
        if self._current_account:
            match = next((a for a in self._accounts if a.id == self._current_account.id), None)
            self._current_account = match or (self._accounts[0] if self._accounts else None)
        else:
            self._current_account = self._accounts[0] if self._accounts else None
        new_name = self._current_account.name if self._current_account else ""
        self._acct_combo_var.set(new_name)
        self._acct_combo.set(new_name)
        self._update_acct_type_label()

    def _update_acct_type_label(self):
        if self._current_account:
            label = ACCOUNT_TYPE_LABELS.get(self._current_account.account_type, "")
            self._acct_type_label.configure(text=f"[{label}]")
        else:
            self._acct_type_label.configure(text="")

    # ── Refresh ──────────────────────────────────────────────────────────────
    def notify_tabs_refresh(self, scope: str = "full"):
        tabs = _REFRESH_SCOPES.get(scope, _REFRESH_SCOPES["full"])
        if "dashboard"  in tabs: self._dashboard_tab.refresh()
        if "register"   in tabs: self._register_tab.refresh()
        if "budgets"    in tabs: self._budgets_tab.refresh()
        if "recurring"  in tabs: self._recurring_tab.refresh()
        if "reports"    in tabs: self._reports_tab.refresh()
        if "net_worth"  in tabs: self._net_worth_tab.refresh()
        if "forecast"   in tabs: self._forecast_tab.refresh()
        if "categories" in tabs: self._categories_tab.refresh()
        if "settings"   in tabs and self._settings_tab: self._settings_tab.refresh()

    # ── Banners & dialogs ────────────────────────────────────────────────────
    def _show_recurring_banner(self, count: int):
        for w in self._banner_frame.winfo_children():
            w.destroy()
        banner = AlertBanner(
            self._banner_frame,
            message=f"{count} recurring transaction{'s' if count != 1 else ''} were automatically added.",
            color="#2196F3",
            action_text="View",
            action_cmd=lambda: self._tabview.set("Register"),
        )
        banner.pack(fill="x", pady=2)

    def _show_reminder_dialog(self):
        if self._startup_reminders:
            ReminderDialog(
                self,
                self._startup_reminders,
                dismissed_reminder_dao=self._dismissed_dao,
                reminder_service=self._reminder_svc,
            )
