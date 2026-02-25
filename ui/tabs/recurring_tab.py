import customtkinter as ctk
from services.recurring_service import RecurringService
from services.account_service import AccountService
from database.category_dao import CategoryDAO
from ui.components.recurring_form import RecurringForm
from ui.components.confirm_dialog import ConfirmDialog
from utils.currency import format_currency
from utils.date_helpers import today, format_display_date


class RecurringTab(ctk.CTkFrame):
    def __init__(
        self,
        master,
        recurring_service: RecurringService,
        account_service: AccountService,
        category_dao: CategoryDAO,
        notify_refresh,
        date_format: str = "MM/DD/YYYY",
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._svc = recurring_service
        self._acct_svc = account_service
        self._cat_dao = category_dao
        self._notify_refresh = notify_refresh
        self._date_format = date_format

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_toolbar()
        self._build_list()
        self._load()

    def refresh(self):
        self._load()

    def _build_toolbar(self):
        bar = ctk.CTkFrame(self, fg_color=("gray88", "gray18"), corner_radius=8)
        bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))
        ctk.CTkLabel(
            bar, text="Recurring Rules",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left", padx=12, pady=8)
        ctk.CTkButton(bar, text="+ Add Rule", command=self._open_add).pack(
            side="right", padx=8, pady=6
        )

    def _build_list(self):
        self._scroll = ctk.CTkScrollableFrame(self)
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self._scroll.grid_columnconfigure(0, weight=1)

    def _load(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        rules = self._svc.get_all()
        if not rules:
            ctk.CTkLabel(
                self._scroll,
                text="No recurring rules yet. Click '+ Add Rule' to create one.",
                text_color="gray60",
            ).grid(row=0, column=0, pady=40)
            return

        # Header
        hdr = ctk.CTkFrame(self._scroll, fg_color=("gray82", "gray22"), corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        for i, (col, w) in enumerate([
            ("Name", 160), ("Type", 70), ("Amount", 90),
            ("Account", 110), ("Category", 110), ("Frequency", 90),
            ("Next Due", 100), ("Status", 70), ("Actions", 80),
        ]):
            ctk.CTkLabel(
                hdr, text=col, width=w, anchor="w",
                font=ctk.CTkFont(weight="bold"),
            ).grid(row=0, column=i, padx=4, pady=4)

        ref = today()
        for idx, rule in enumerate(rules):
            self._add_row(idx + 1, rule, ref)

    def _add_row(self, idx, rule, ref):
        bg = ("gray92", "gray17") if idx % 2 == 0 else ("gray88", "gray21")
        row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=4)
        row.grid(row=idx, column=0, sticky="ew", pady=1, padx=2)

        next_due = self._svc.next_due_date(rule)
        next_due_str = format_display_date(next_due.strftime("%Y-%m-%d"), self._date_format) if next_due else "—"
        status_text = "Active" if rule.is_active else "Inactive"
        status_color = "#4CAF50" if rule.is_active else "gray60"

        data = [
            (rule.name, 160),
            (rule.type.title(), 70),
            (format_currency(rule.amount), 90),
            (rule.account_name, 110),
            (rule.category_name, 110),
            (rule.frequency.title(), 90),
            (next_due_str, 100),
        ]
        for i, (text, width) in enumerate(data):
            ctk.CTkLabel(row, text=text, width=width, anchor="w").grid(
                row=0, column=i, padx=4, pady=4
            )

        ctk.CTkLabel(
            row, text=status_text, width=70, anchor="w",
            text_color=status_color,
        ).grid(row=0, column=7, padx=4)

        acts = ctk.CTkFrame(row, fg_color="transparent")
        acts.grid(row=0, column=8, padx=(4, 6))
        ctk.CTkButton(
            acts, text="Edit", width=40, height=24,
            command=lambda r=rule: self._open_edit(r),
        ).pack(side="left", padx=2)
        toggle_text = "Pause" if rule.is_active else "Resume"
        ctk.CTkButton(
            acts, text=toggle_text, width=52, height=24,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"),
            command=lambda r=rule: self._toggle_active(r),
        ).pack(side="left")

    def _open_add(self):
        form = RecurringForm(
            self.winfo_toplevel(),
            self._svc, self._acct_svc, self._cat_dao,
            date_format=self._date_format,
        )
        self.wait_window(form)
        if form.saved:
            self._notify_refresh("recurring")

    def _open_edit(self, rule):
        form = RecurringForm(
            self.winfo_toplevel(),
            self._svc, self._acct_svc, self._cat_dao,
            rule=rule,
            date_format=self._date_format,
        )
        self.wait_window(form)
        if form.saved:
            self._notify_refresh("recurring")

    def _toggle_active(self, rule):
        self._svc.set_active(rule.id, not rule.is_active)
        self._notify_refresh("recurring")
