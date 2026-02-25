import customtkinter as ctk
from services.budget_service import BudgetService
from ui.components.budget_form import BudgetForm
from ui.components.confirm_dialog import ConfirmDialog
from utils.currency import format_currency
from utils.date_helpers import current_month_str, friendly_month, prev_month, next_month


class BudgetsTab(ctk.CTkFrame):
    def __init__(
        self,
        master,
        budget_service: BudgetService,
        notify_refresh,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._svc = budget_service
        self._notify_refresh = notify_refresh
        self._month_var = ctk.StringVar(value=current_month_str())

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

        ctk.CTkButton(bar, text="◀", width=28, command=self._prev_month).pack(side="left", padx=(8, 0), pady=6)
        self._mlabel = ctk.CTkLabel(
            bar, textvariable=self._month_var, width=130, anchor="center",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self._mlabel.pack(side="left", padx=4)
        ctk.CTkButton(bar, text="▶", width=28, command=self._next_month).pack(side="left", padx=(0, 12))

        ctk.CTkButton(bar, text="+ Add Budget", command=self._open_add).pack(side="left", padx=4)
        ctk.CTkButton(
            bar, text="Copy from Previous Month",
            command=self._copy_prev,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"),
        ).pack(side="left", padx=4)

    def _prev_month(self):
        self._month_var.set(prev_month(self._month_var.get()))
        self._load()

    def _next_month(self):
        self._month_var.set(next_month(self._month_var.get()))
        self._load()

    def _build_list(self):
        self._scroll = ctk.CTkScrollableFrame(self)
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self._scroll.grid_columnconfigure(0, weight=1)

    def _load(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        month = self._month_var.get()
        budgets = self._svc.get_budget_status(month)
        if not budgets:
            ctk.CTkLabel(
                self._scroll,
                text="No budgets set for this month. Click '+ Add Budget' to create one.",
                text_color="gray60",
            ).grid(row=0, column=0, pady=40)
            return

        for idx, b in enumerate(budgets):
            self._add_budget_card(idx, b)

    def _add_budget_card(self, idx, b):
        card = ctk.CTkFrame(
            self._scroll, fg_color=("gray90", "gray20"), corner_radius=8
        )
        card.grid(row=idx, column=0, sticky="ew", padx=4, pady=4)
        card.grid_columnconfigure(0, weight=1)

        # Header row
        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr, text=b.category_name,
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
        ).grid(row=0, column=0, sticky="w")

        pct = b.percentage
        pct_text = f"{pct*100:.1f}%"
        pct_color = "#4CAF50" if pct < 0.8 else ("#FF9800" if pct < 1.0 else "#F44336")
        ctk.CTkLabel(hdr, text=pct_text, text_color=pct_color).grid(row=0, column=1, padx=(8, 0))

        ctk.CTkButton(
            hdr, text="Edit", width=50, height=24,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"),
            command=lambda budget=b: self._open_edit(budget),
        ).grid(row=0, column=2, padx=(8, 0))

        # Amounts
        ctk.CTkLabel(
            card,
            text=f"Spent: {format_currency(b.spent_amount)}  /  Limit: {format_currency(b.limit_amount)}  |  Remaining: {format_currency(b.remaining)}",
            text_color="gray60", anchor="w",
        ).grid(row=1, column=0, padx=12, sticky="ew")

        # Progress bar
        bar = ctk.CTkProgressBar(card, progress_color=pct_color)
        bar.grid(row=2, column=0, padx=12, pady=(4, 10), sticky="ew")
        bar.set(min(pct, 1.0))

    def _open_add(self):
        form = BudgetForm(
            self.winfo_toplevel(), self._svc, month=self._month_var.get()
        )
        self.wait_window(form)
        if form.saved:
            self._notify_refresh("budget")

    def _open_edit(self, budget):
        form = BudgetForm(
            self.winfo_toplevel(), self._svc,
            month=self._month_var.get(), budget=budget
        )
        self.wait_window(form)
        if form.saved:
            self._notify_refresh("budget")

    def _copy_prev(self):
        count = self._svc.copy_from_previous_month(self._month_var.get())
        self._load()
        if count == 0:
            ctk.CTkLabel(
                self._scroll,
                text="No budgets in previous month to copy.",
                text_color="gray60",
            ).grid(row=0, column=0, pady=40)
