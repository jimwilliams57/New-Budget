import customtkinter as ctk
from services.transaction_service import TransactionService
from services.budget_service import BudgetService
from utils.currency import format_currency
from utils.date_helpers import current_month_str, friendly_month, prev_month, next_month, format_display_date


class DashboardTab(ctk.CTkFrame):
    def __init__(
        self,
        master,
        tx_service: TransactionService,
        budget_service: BudgetService,
        get_account_id,   # callable → int | None
        get_account=None, # callable → Account | None
        date_format: str = "MM/DD/YYYY",
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._tx_svc = tx_service
        self._budget_svc = budget_service
        self._get_account_id = get_account_id
        self._get_account = get_account or (lambda: None)
        self._date_format = date_format
        self._month_var = ctk.StringVar(value=current_month_str())

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_month_nav()
        self._build_summary_cards()
        self._build_bottom_section()
        self._load()

    def refresh(self):
        self._load()

    def _build_month_nav(self):
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 0))
        ctk.CTkButton(nav, text="◀", width=28, command=self._prev_month).pack(side="left")
        self._month_label = ctk.CTkLabel(
            nav, textvariable=self._month_var,
            font=ctk.CTkFont(size=15, weight="bold"), width=130, anchor="center"
        )
        self._month_label.pack(side="left", padx=8)
        ctk.CTkButton(nav, text="▶", width=28, command=self._next_month).pack(side="left")

    def _prev_month(self):
        self._month_var.set(prev_month(self._month_var.get()))
        self._load()

    def _next_month(self):
        self._month_var.set(next_month(self._month_var.get()))
        self._load()

    def _build_summary_cards(self):
        self._card_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._card_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=12)
        self._card_frame.grid_columnconfigure((0, 1, 2), weight=1)

    def _build_bottom_section(self):
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 12))
        bottom.grid_columnconfigure(0, weight=1)
        bottom.grid_columnconfigure(1, weight=1)
        bottom.grid_rowconfigure(0, weight=1)

        # Recent transactions
        self._recent_frame = ctk.CTkScrollableFrame(
            bottom, label_text="Recent Transactions", height=240
        )
        self._recent_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # Budget progress
        self._budget_frame = ctk.CTkScrollableFrame(
            bottom, label_text="Budget Progress (This Month)", height=240
        )
        self._budget_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

    def _load(self):
        account_id = self._get_account_id()
        account = self._get_account()
        month = self._month_var.get()
        self._month_var.set(month)  # trigger label update
        is_debt = account is not None and account.is_debt_account

        # Pre-fetch monthly pairs once — used for both cards and recent transactions
        month_pairs = self._tx_svc.get_with_running_balance(account_id, month) if account_id else []

        # Summary cards
        for w in self._card_frame.winfo_children():
            w.destroy()

        if is_debt and account_id:
            # All-time running balance → amount owed
            all_pairs = self._tx_svc.get_with_running_balance(account_id)
            current_balance = all_pairs[-1][1] if all_pairs else 0.0
            amount_owed = account.opening_balance - current_balance
            # Derive monthly activity from pre-fetched pairs (avoids a separate get_totals() query)
            monthly_expense = sum(tx.amount for tx, _ in month_pairs if tx.type == "expense")
            monthly_income = sum(tx.amount for tx, _ in month_pairs if tx.type == "income")
            card_data = [
                ("Amount Owed",          amount_owed,     "#F44336" if amount_owed > 0 else "#4CAF50", ""),
                ("Charges This Month",   monthly_expense, "#FF9800",  ""),
                ("Payments This Month",  monthly_income,  "#4CAF50",  ""),
            ]
        else:
            if account_id:
                totals = self._tx_svc.get_totals(account_id, month)
            else:
                totals = {"income": 0.0, "expense": 0.0, "net": 0.0}
            card_data = [
                ("Income",   totals["income"],  "#4CAF50",  None),
                ("Expenses", totals["expense"], "#F44336",  None),
                ("Net",      totals["net"],     "#2196F3" if totals.get("net", 0) >= 0 else "#FF9800", None),
            ]

        for i, (label, value, color, prefix) in enumerate(card_data):
            self._make_card(self._card_frame, i, label, value, color, prefix=prefix)

        # Recent transactions
        for w in self._recent_frame.winfo_children():
            w.destroy()
        if account_id:
            pairs = month_pairs  # reuse pre-fetched result
            recent = list(reversed(pairs[-10:]))  # last 10
            for idx, (tx, balance) in enumerate(recent):
                bg = ("gray90", "gray20") if idx % 2 == 0 else ("gray86", "gray24")
                f = ctk.CTkFrame(self._recent_frame, fg_color=bg, corner_radius=4)
                f.pack(fill="x", pady=1)
                f.grid_columnconfigure(1, weight=1)

                if is_debt:
                    color = "#F44336" if tx.type == "expense" else (
                        "#4CAF50" if tx.type == "income" else "#2196F3"
                    )
                    sign = "+" if tx.type == "expense" else ("-" if tx.type == "income" else "~")
                else:
                    color = "#4CAF50" if tx.type == "income" else (
                        "#F44336" if tx.type == "expense" else "#2196F3"
                    )
                    sign = "+" if tx.type == "income" else ("-" if tx.type == "expense" else "~")

                ctk.CTkLabel(
                    f, text=format_display_date(tx.date, self._date_format), width=85, anchor="w"
                ).grid(row=0, column=0, padx=6, pady=3)
                ctk.CTkLabel(f, text=tx.description or tx.category_name, anchor="w").grid(
                    row=0, column=1, padx=4, sticky="ew"
                )
                ctk.CTkLabel(
                    f, text=f"{sign}{format_currency(tx.amount)}",
                    text_color=color, anchor="e", width=100,
                ).grid(row=0, column=2, padx=6)

        # Budget progress bars
        for w in self._budget_frame.winfo_children():
            w.destroy()
        current_month = current_month_str()
        budgets = self._budget_svc.get_budget_status(month)
        if not budgets:
            ctk.CTkLabel(
                self._budget_frame, text="No budgets set for this month.",
                text_color="gray60",
            ).pack(pady=20)
        for b in budgets:
            pct = min(b.percentage, 1.0)
            bar_color = "#4CAF50" if pct < 0.8 else ("#FF9800" if pct < 1.0 else "#F44336")
            f = ctk.CTkFrame(self._budget_frame, fg_color="transparent")
            f.pack(fill="x", pady=4, padx=4)
            top_row = ctk.CTkFrame(f, fg_color="transparent")
            top_row.pack(fill="x")
            ctk.CTkLabel(top_row, text=b.category_name, anchor="w").pack(side="left")
            ctk.CTkLabel(
                top_row,
                text=f"{format_currency(b.spent_amount)} / {format_currency(b.limit_amount)}",
                anchor="e", text_color="gray60",
            ).pack(side="right")
            ctk.CTkProgressBar(f, progress_color=bar_color).pack(fill="x", pady=2)
            f.winfo_children()[-1].set(pct)

    def _make_card(self, parent, col, label, value, color, prefix=None):
        card = ctk.CTkFrame(parent, fg_color=("gray90", "gray20"), corner_radius=10)
        card.grid(row=0, column=col, padx=6, sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card, text=label, font=ctk.CTkFont(size=12),
            text_color="gray60",
        ).grid(row=0, column=0, pady=(12, 0), padx=16)

        if prefix is not None:
            # Explicit prefix supplied (e.g. "" for debt cards)
            display_text = f"{prefix}{format_currency(abs(value))}"
        else:
            # Original behaviour: auto-compute sign from label
            display_text = f"{'+' if label != 'Expenses' and value >= 0 else ''}{format_currency(abs(value))}"

        ctk.CTkLabel(
            card,
            text=display_text,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=color,
        ).grid(row=1, column=0, pady=(4, 12), padx=16)
