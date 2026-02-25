import customtkinter as ctk
from services.transaction_service import TransactionService
from services.account_service import AccountService
from database.category_dao import CategoryDAO
from models.transaction import Transaction
from ui.components.date_picker import DatePickerWidget
from utils.date_helpers import today_str


class TransactionForm(ctk.CTkToplevel):
    """Add or edit a transaction (income, expense, or transfer)."""

    _last_date: str = today_str()  # reset to today on each app launch

    def __init__(
        self,
        master,
        tx_service: TransactionService,
        account_service: AccountService,
        category_dao: CategoryDAO,
        current_account_id: int,
        initial_type: str = "expense",
        transaction: Transaction | None = None,
        date_format: str = "MM/DD/YYYY",
        payment_to_current_account: bool = False,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._tx_svc = tx_service
        self._acct_svc = account_service
        self._cat_dao = category_dao
        self._current_account_id = current_account_id
        self._transaction = transaction
        self._date_format = date_format
        self._payment_to_current_account = payment_to_current_account
        self.saved = False

        is_transfer = initial_type == "transfer" or (
            transaction and transaction.type == "transfer"
        )
        if transaction:
            initial_type = transaction.type

        self._type = initial_type
        self.title(f"{'Edit' if transaction else 'Add'} {initial_type.title()}")
        self.resizable(False, False)
        self.grid_columnconfigure(1, weight=1)

        self._accounts = account_service.get_all()
        account_names = [a.name for a in self._accounts]

        row = 0

        if is_transfer or initial_type == "transfer":
            self._build_transfer_form(row, account_names, transaction)
        else:
            self._build_standard_form(row, initial_type, transaction)

        self.transient(master)
        self.grab_set()
        self._center()

    def _label(self, text, row):
        ctk.CTkLabel(self, text=text).grid(
            row=row, column=0, padx=(16, 8), pady=4, sticky="e"
        )

    def _build_standard_form(self, start_row, type_: str, tx: Transaction | None):
        r = start_row

        # Type selector (income/expense) — only for new transactions
        if not tx:
            self._label("Type:", r)
            self._type_var = ctk.StringVar(value=type_)
            type_frame = ctk.CTkFrame(self, fg_color="transparent")
            type_frame.grid(row=r, column=1, padx=(0, 16), pady=4, sticky="w")
            for t in ("income", "expense"):
                ctk.CTkRadioButton(
                    type_frame, text=t.title(),
                    variable=self._type_var, value=t,
                    command=self._on_type_change,
                ).pack(side="left", padx=4)
            r += 1
        else:
            self._type_var = ctk.StringVar(value=type_)

        # Description
        self._label("Description:", r)
        self._desc_var = ctk.StringVar(value=tx.description if tx else "")
        ctk.CTkEntry(self, textvariable=self._desc_var, width=200).grid(
            row=r, column=1, padx=(0, 16), pady=4, sticky="ew"
        )
        r += 1

        # Amount
        self._label("Amount:", r)
        self._amount_var = ctk.StringVar(
            value=f"{tx.amount:.2f}" if tx else ""
        )
        ctk.CTkEntry(self, textvariable=self._amount_var, width=200).grid(
            row=r, column=1, padx=(0, 16), pady=4, sticky="ew"
        )
        r += 1

        # Date
        self._label("Date:", r)
        self._date_picker = DatePickerWidget(
            self,
            initial_date=tx.date if tx else TransactionForm._last_date,
            date_format=self._date_format,
        )
        self._date_picker.grid(row=r, column=1, padx=(0, 16), pady=4, sticky="w")
        r += 1

        # Category
        self._label("Category:", r)
        self._cats = self._cat_dao.get_for_transaction_type(self._type_var.get())
        self._cat_names = [c.name for c in self._cats]
        current_cat = ""
        if tx and tx.category_name:
            current_cat = tx.category_name
        elif self._cat_names:
            current_cat = self._cat_names[0]
        self._cat_var = ctk.StringVar(value=current_cat)
        self._cat_combo = ctk.CTkComboBox(
            self, values=self._cat_names,
            variable=self._cat_var, width=200, state="readonly"
        )
        self._cat_combo.grid(row=r, column=1, padx=(0, 16), pady=4, sticky="ew")
        r += 1

        # Cleared
        self._label("Cleared:", r)
        self._cleared_var = ctk.BooleanVar(value=tx.cleared if tx else False)
        ctk.CTkCheckBox(self, text="", variable=self._cleared_var).grid(
            row=r, column=1, padx=(0, 16), pady=4, sticky="w"
        )
        r += 1

        self._build_footer(r, is_transfer=False)

    def _build_transfer_form(self, start_row, account_names, tx: Transaction | None):
        r = start_row
        self._type = "transfer"

        current_from_name = ""
        for a in self._accounts:
            if a.id == self._current_account_id:
                current_from_name = a.name
        other_accounts = [a.name for a in self._accounts if a.id != self._current_account_id]

        # From account
        self._label("From Account:", r)
        if self._payment_to_current_account:
            from_default = other_accounts[0] if other_accounts else ""
        else:
            from_default = current_from_name
        self._from_var = ctk.StringVar(value=from_default)
        ctk.CTkComboBox(
            self, values=account_names,
            variable=self._from_var, width=200, state="readonly"
        ).grid(row=r, column=1, padx=(0, 16), pady=4, sticky="ew")
        r += 1

        # To account
        self._label("To Account:", r)
        if self._payment_to_current_account:
            to_default = current_from_name
        else:
            to_default = other_accounts[0] if other_accounts else ""
        self._to_var = ctk.StringVar(value=to_default)
        ctk.CTkComboBox(
            self, values=account_names,
            variable=self._to_var, width=200, state="readonly"
        ).grid(row=r, column=1, padx=(0, 16), pady=4, sticky="ew")
        r += 1

        # Amount
        self._label("Amount:", r)
        self._amount_var = ctk.StringVar(
            value=f"{tx.amount:.2f}" if tx else ""
        )
        ctk.CTkEntry(self, textvariable=self._amount_var, width=200).grid(
            row=r, column=1, padx=(0, 16), pady=4, sticky="ew"
        )
        r += 1

        # Date
        self._label("Date:", r)
        self._date_picker = DatePickerWidget(
            self,
            initial_date=tx.date if tx else TransactionForm._last_date,
            date_format=self._date_format,
        )
        self._date_picker.grid(row=r, column=1, padx=(0, 16), pady=4, sticky="w")
        r += 1

        # Description
        self._label("Description:", r)
        self._desc_var = ctk.StringVar(value=tx.description if tx else "")
        ctk.CTkEntry(self, textvariable=self._desc_var, width=200).grid(
            row=r, column=1, padx=(0, 16), pady=4, sticky="ew"
        )
        r += 1

        self._build_footer(r, is_transfer=True)

    def _build_footer(self, r, is_transfer: bool):
        self._error_var = ctk.StringVar()
        ctk.CTkLabel(
            self, textvariable=self._error_var,
            text_color="#F44336", wraplength=280, anchor="w"
        ).grid(row=r, column=0, columnspan=2, padx=16, pady=(0, 4), sticky="ew")
        r += 1

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=r, column=0, columnspan=2, padx=16, pady=(4, 16), sticky="ew")
        ctk.CTkButton(
            btn_frame, text="Cancel", width=90,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"),
            command=self.destroy,
        ).pack(side="left")
        save_text = "Save Transfer" if is_transfer else "Save"
        ctk.CTkButton(
            btn_frame, text=save_text, width=110,
            command=self._on_save,
        ).pack(side="right")

    def _on_type_change(self):
        t = self._type_var.get()
        self._cats = self._cat_dao.get_for_transaction_type(t)
        self._cat_names = [c.name for c in self._cats]
        self._cat_combo.configure(values=self._cat_names)
        if self._cat_names:
            self._cat_var.set(self._cat_names[0])
            self._cat_combo.set(self._cat_names[0])

    def _on_save(self):
        try:
            amount = float(self._amount_var.get())
        except ValueError:
            self._error_var.set("Invalid amount.")
            return

        if not self._date_picker.is_valid():
            self._error_var.set("Invalid date.")
            return

        date_str = self._date_picker.get()
        desc = self._desc_var.get().strip()

        try:
            if self._type == "transfer":
                from_name = self._from_var.get()
                to_name = self._to_var.get()
                from_acct = next((a for a in self._accounts if a.name == from_name), None)
                to_acct = next((a for a in self._accounts if a.name == to_name), None)
                if not from_acct or not to_acct:
                    self._error_var.set("Please select both accounts.")
                    return
                self._tx_svc.create_transfer(
                    from_acct.id, to_acct.id, amount, date_str, desc
                )
            else:
                type_ = self._type_var.get()
                cat_name = self._cat_var.get()
                cat = next((c for c in self._cats if c.name == cat_name), None)
                if not cat:
                    self._error_var.set("Please select a category.")
                    return

                if self._transaction:
                    self._tx_svc.update(
                        self._transaction.id, type_, amount, date_str,
                        cat.id, desc, self._cleared_var.get()
                    )
                else:
                    self._tx_svc.create_income_expense(
                        account_id=self._current_account_id,
                        type_=type_,
                        amount=amount,
                        date=date_str,
                        category_id=cat.id,
                        description=desc,
                        cleared=self._cleared_var.get(),
                    )
            TransactionForm._last_date = self._date_picker.get()
            self.saved = True
            self.destroy()
        except ValueError as e:
            self._error_var.set(str(e))

    def _center(self):
        self.update_idletasks()
        mw = self.master.winfo_x() + self.master.winfo_width() // 2
        mh = self.master.winfo_y() + self.master.winfo_height() // 2
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        self.geometry(f"+{mw - w//2}+{mh - h//2}")
