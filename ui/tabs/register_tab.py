import customtkinter as ctk
from services.transaction_service import TransactionService
from services.account_service import AccountService
from database.category_dao import CategoryDAO
from models.transaction import Transaction
from ui.components.transaction_form import TransactionForm
from ui.components.confirm_dialog import ConfirmDialog
from utils.currency import format_currency
from utils.date_helpers import current_month_str, friendly_month, format_display_date


_MAX_RENDERED_ROWS = 100


class RegisterTab(ctk.CTkFrame):
    def __init__(
        self,
        master,
        tx_service: TransactionService,
        account_service: AccountService,
        category_dao: CategoryDAO,
        get_account_id,   # callable → int | None
        notify_refresh,   # callable
        get_account=None, # callable → Account | None
        date_format: str = "MM/DD/YYYY",
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._tx_svc = tx_service
        self._acct_svc = account_service
        self._cat_dao = category_dao
        self._get_account_id = get_account_id
        self._get_account = get_account or (lambda: None)
        self._notify_refresh = notify_refresh
        self._date_format = date_format

        self._month_var = ctk.StringVar(value=current_month_str())
        self._type_var = ctk.StringVar(value="all")
        self._cleared_var = ctk.StringVar(value="all")
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._load())

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_filter_bar()
        self._build_header()
        self._build_register()
        self._load()

    def refresh(self):
        self._load()

    # ── Filter bar ──────────────────────────────────────────────────────────
    def _build_filter_bar(self):
        bar = ctk.CTkFrame(self, fg_color=("gray88", "gray18"), corner_radius=8)
        bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))
        bar.grid_columnconfigure(4, weight=1)

        # Month nav
        ctk.CTkButton(bar, text="◀", width=28, command=self._prev_month).grid(
            row=0, column=0, padx=(8, 0), pady=6
        )
        self._month_label = ctk.CTkLabel(
            bar, textvariable=self._month_var, width=90, anchor="center"
        )
        self._month_label.grid(row=0, column=1, padx=4)
        ctk.CTkButton(bar, text="▶", width=28, command=self._next_month).grid(
            row=0, column=2, padx=(0, 8)
        )

        # Type filter
        ctk.CTkSegmentedButton(
            bar,
            values=["all", "income", "expense", "transfer"],
            variable=self._type_var,
            command=lambda _: self._load(),
            width=280,
        ).grid(row=0, column=3, padx=8)

        # Cleared filter
        ctk.CTkSegmentedButton(
            bar,
            values=["all", "cleared", "pending"],
            variable=self._cleared_var,
            command=lambda _: self._load(),
            width=200,
        ).grid(row=0, column=4, padx=8)

        # Search
        ctk.CTkEntry(
            bar, textvariable=self._search_var,
            placeholder_text="Search…", width=160,
        ).grid(row=0, column=5, padx=8)

        # Button frame — populated by _rebuild_action_buttons()
        self._btn_frame = ctk.CTkFrame(bar, fg_color="transparent")
        self._btn_frame.grid(row=0, column=6, padx=(0, 8))

    def _rebuild_action_buttons(self, account):
        for w in self._btn_frame.winfo_children():
            w.destroy()

        is_debt = account is not None and account.is_debt_account

        if is_debt:
            buttons = [
                ("+ Charge",     lambda: self._open_add_form("expense")),
                ("Make Payment", self._open_make_payment),
                ("+ Transfer",   lambda: self._open_add_form("transfer")),
            ]
        else:
            buttons = [
                ("+ Income",   lambda: self._open_add_form("income")),
                ("+ Expense",  lambda: self._open_add_form("expense")),
                ("+ Transfer", lambda: self._open_add_form("transfer")),
            ]

        for label, cmd in buttons:
            ctk.CTkButton(
                self._btn_frame, text=label, width=88,
                command=cmd,
            ).pack(side="left", padx=2)

    def _prev_month(self):
        from utils.date_helpers import prev_month
        self._month_var.set(prev_month(self._month_var.get()))
        self._load()

    def _next_month(self):
        from utils.date_helpers import next_month
        self._month_var.set(next_month(self._month_var.get()))
        self._load()

    # ── Column headers ───────────────────────────────────────────────────────
    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=("gray82", "gray22"), corner_radius=0)
        hdr.grid(row=1, column=0, sticky="ew", padx=8, pady=(4, 0))
        cols = [("✓", 30), ("Date", 85), ("Type", 72), ("Category", 130),
                ("Description", 180), ("Amount", 90), ("Balance", 90), ("Actions", 100)]
        for i, (label, width) in enumerate(cols):
            lbl = ctk.CTkLabel(
                hdr, text=label, width=width, anchor="w",
                font=ctk.CTkFont(weight="bold"),
            )
            lbl.grid(row=0, column=i, padx=4, pady=4, sticky="w")
            if label == "Balance":
                self._balance_header = lbl

    # ── Scrollable register ──────────────────────────────────────────────────
    def _build_register(self):
        self._scroll = ctk.CTkScrollableFrame(self)
        self._scroll.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self._scroll.grid_columnconfigure(0, weight=1)

    def _load(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        account_id = self._get_account_id()
        account = self._get_account()
        is_debt = account is not None and account.is_debt_account

        # Rebuild action buttons based on account type
        self._rebuild_action_buttons(account)

        # Update balance column header
        self._balance_header.configure(text="Amt Owed" if is_debt else "Balance")

        if not account_id:
            ctk.CTkLabel(self._scroll, text="No account selected.").grid(row=0, column=0)
            return

        month = self._month_var.get()
        type_f = self._type_var.get()
        cleared_f = self._cleared_var.get()
        search = self._search_var.get().strip()

        rows = self._tx_svc.get_with_running_balance(
            account_id, month, type_f, cleared_f, search
        )

        if not rows:
            ctk.CTkLabel(
                self._scroll, text="No transactions for this period.",
                text_color="gray60",
            ).grid(row=0, column=0, pady=20)
            return

        total = len(rows)
        visible = rows[:_MAX_RENDERED_ROWS]
        for idx, (tx, balance) in enumerate(visible):
            self._add_row(idx, tx, balance, account, is_debt)

        if total > _MAX_RENDERED_ROWS:
            ctk.CTkLabel(
                self._scroll,
                text=f"Showing {_MAX_RENDERED_ROWS} of {total} transactions — use filters or search to narrow results.",
                text_color="gray60",
                font=ctk.CTkFont(size=11),
            ).grid(row=_MAX_RENDERED_ROWS, column=0, pady=8)

    def _add_row(self, idx: int, tx: Transaction, balance: float, account=None, is_debt: bool = False):
        bg = ("gray92", "gray17") if idx % 2 == 0 else ("gray88", "gray21")
        row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=4)
        row.grid(row=idx, column=0, sticky="ew", pady=1, padx=2)

        # Cleared checkbox
        cleared_var = ctk.BooleanVar(value=tx.cleared)
        ctk.CTkCheckBox(
            row, text="", variable=cleared_var, width=30,
            command=lambda t=tx, v=cleared_var: self._toggle_cleared(t, v),
        ).grid(row=0, column=0, padx=(6, 0), pady=4)

        # Date
        ctk.CTkLabel(
            row, text=format_display_date(tx.date, self._date_format), width=85, anchor="w"
        ).grid(row=0, column=1, padx=4, pady=4)

        # Type badge
        type_colors = {
            "income": "#4CAF50", "expense": "#F44336", "transfer": "#2196F3"
        }
        ctk.CTkLabel(
            row, text=tx.type.title(), width=72, anchor="w",
            text_color=type_colors.get(tx.type, "gray"),
        ).grid(row=0, column=2, padx=4)

        # Category
        ctk.CTkLabel(row, text=tx.category_name or "—", width=130, anchor="w").grid(
            row=0, column=3, padx=4
        )

        # Description
        ctk.CTkLabel(row, text=tx.description or "—", width=180, anchor="w").grid(
            row=0, column=4, padx=4
        )

        # Amount
        if tx.type == "income":
            amt_color = "#4CAF50"
            amt_text = f"+{format_currency(tx.amount)}"
        elif tx.type == "expense":
            amt_color = "#F44336"
            amt_text = f"-{format_currency(tx.amount)}"
        else:
            # Transfer: determine direction via pair
            pair = self._tx_svc.get_transfer_pair(tx.transfer_pair_id) if tx.transfer_pair_id else []
            if len(pair) == 2:
                debit_id = min(p.id for p in pair)
                if tx.id == debit_id:
                    amt_color = "#F44336"
                    amt_text = f"-{format_currency(tx.amount)}"
                else:
                    amt_color = "#4CAF50"
                    amt_text = f"+{format_currency(tx.amount)}"
            else:
                amt_color = "#2196F3"
                amt_text = format_currency(tx.amount)

        ctk.CTkLabel(
            row, text=amt_text, width=90, anchor="e", text_color=amt_color
        ).grid(row=0, column=5, padx=4)

        # Balance / Amount Owed
        if is_debt and account is not None:
            display_balance = account.opening_balance - balance
            bal_color = "#F44336" if display_balance > 0 else "#4CAF50"
        else:
            display_balance = balance
            bal_color = "#4CAF50" if balance >= 0 else "#F44336"

        ctk.CTkLabel(
            row, text=format_currency(display_balance), width=90, anchor="e",
            text_color=bal_color,
        ).grid(row=0, column=6, padx=4)

        # Actions
        acts = ctk.CTkFrame(row, fg_color="transparent")
        acts.grid(row=0, column=7, padx=(4, 6))
        ctk.CTkButton(
            acts, text="Edit", width=44, height=24,
            command=lambda t=tx: self._open_edit_form(t),
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            acts, text="Del", width=38, height=24,
            fg_color="#F44336", hover_color="#D32F2F",
            command=lambda t=tx: self._delete_tx(t),
        ).pack(side="left")

    def _toggle_cleared(self, tx: Transaction, var: ctk.BooleanVar):
        self._tx_svc.set_cleared(tx.id, var.get())

    def _open_add_form(self, type_: str):
        account_id = self._get_account_id()
        if not account_id:
            return
        form = TransactionForm(
            self.winfo_toplevel(),
            self._tx_svc, self._acct_svc, self._cat_dao,
            current_account_id=account_id,
            initial_type=type_,
            date_format=self._date_format,
        )
        self.wait_window(form)
        if form.saved:
            self._notify_refresh("transaction")

    def _open_make_payment(self):
        account_id = self._get_account_id()
        if not account_id:
            return
        form = TransactionForm(
            self.winfo_toplevel(),
            self._tx_svc, self._acct_svc, self._cat_dao,
            current_account_id=account_id,
            initial_type="transfer",
            payment_to_current_account=True,
            date_format=self._date_format,
        )
        self.wait_window(form)
        if form.saved:
            self._notify_refresh("transaction")

    def _open_edit_form(self, tx: Transaction):
        account_id = self._get_account_id()
        form = TransactionForm(
            self.winfo_toplevel(),
            self._tx_svc, self._acct_svc, self._cat_dao,
            current_account_id=account_id,
            initial_type=tx.type,
            transaction=tx,
            date_format=self._date_format,
        )
        self.wait_window(form)
        if form.saved:
            self._notify_refresh("transaction")

    def _delete_tx(self, tx: Transaction):
        if tx.transfer_pair_id:
            dlg = ConfirmDialog(
                self.winfo_toplevel(),
                "Delete Transfer",
                "This is part of a transfer. Delete both sides of this transfer?",
            )
            if dlg.result:
                self._tx_svc.delete_transfer_pair(tx.transfer_pair_id)
                self._notify_refresh("transaction")
        else:
            dlg = ConfirmDialog(
                self.winfo_toplevel(),
                "Delete Transaction",
                f"Delete this {tx.type} of {format_currency(tx.amount)}?",
            )
            if dlg.result:
                self._tx_svc.delete(tx.id)
                self._notify_refresh("transaction")
