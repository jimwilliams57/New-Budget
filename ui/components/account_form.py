import customtkinter as ctk
from services.account_service import AccountService
from models.account import Account, ACCOUNT_TYPE_LABELS, DEBT_ACCOUNT_TYPES


class AccountForm(ctk.CTkToplevel):
    """Add or edit an account. Sets self.saved = True on success."""

    # Maps display label → internal key
    _TYPE_OPTIONS = list(ACCOUNT_TYPE_LABELS.values())  # ["Checking", "Savings", "Loan", "Credit Card"]
    _LABEL_TO_KEY = {v: k for k, v in ACCOUNT_TYPE_LABELS.items()}

    def __init__(
        self,
        master,
        account_service: AccountService,
        account: Account | None = None,
        on_delete_callback=None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._svc = account_service
        self._account = account
        self._on_delete = on_delete_callback
        self.saved = False

        self.title("Edit Account" if account else "New Account")
        self.resizable(False, False)
        self.grid_columnconfigure(1, weight=1)

        # Row 0 — Name
        ctk.CTkLabel(self, text="Name:").grid(
            row=0, column=0, padx=(16, 8), pady=(16, 4), sticky="e"
        )
        self._name_var = ctk.StringVar(value=account.name if account else "")
        self._name_entry = ctk.CTkEntry(self, textvariable=self._name_var, width=240)
        self._name_entry.grid(row=0, column=1, padx=(0, 16), pady=(16, 4), sticky="ew")

        # Row 1 — Description
        ctk.CTkLabel(self, text="Description:").grid(
            row=1, column=0, padx=(16, 8), pady=4, sticky="e"
        )
        self._desc_var = ctk.StringVar(value=account.description if account else "")
        ctk.CTkEntry(self, textvariable=self._desc_var, width=240).grid(
            row=1, column=1, padx=(0, 16), pady=4, sticky="ew"
        )

        # Row 2 — Account Type
        ctk.CTkLabel(self, text="Account Type:").grid(
            row=2, column=0, padx=(16, 8), pady=4, sticky="e"
        )
        initial_type_label = ACCOUNT_TYPE_LABELS.get(
            account.account_type if account else "checking", "Checking"
        )
        self._type_var = ctk.StringVar(value=initial_type_label)
        self._type_combo = ctk.CTkComboBox(
            self,
            values=self._TYPE_OPTIONS,
            variable=self._type_var,
            width=240,
            state="readonly",
            command=self._on_type_change,
        )
        self._type_combo.grid(row=2, column=1, padx=(0, 16), pady=4, sticky="ew")

        # Row 3 — Opening Balance (only for debt accounts)
        self._ob_label = ctk.CTkLabel(self, text="Opening Balance ($):")
        self._ob_label.grid(row=3, column=0, padx=(16, 8), pady=4, sticky="e")
        self._ob_var = ctk.StringVar(
            value=f"{account.opening_balance:.2f}" if account and account.is_debt_account else ""
        )
        self._ob_entry = ctk.CTkEntry(self, textvariable=self._ob_var, width=240)
        self._ob_entry.grid(row=3, column=1, padx=(0, 16), pady=4, sticky="ew")
        self._ob_hint = ctk.CTkLabel(
            self, text="Enter the current amount owed",
            text_color="gray60", font=ctk.CTkFont(size=11)
        )
        self._ob_hint.grid(row=4, column=1, padx=(0, 16), pady=(0, 4), sticky="w")

        # Row 5 — Error label
        self._error_var = ctk.StringVar()
        self._error_label = ctk.CTkLabel(
            self, textvariable=self._error_var, text_color="#F44336",
            wraplength=280, anchor="w"
        )
        self._error_label.grid(
            row=5, column=0, columnspan=2, padx=16, pady=(0, 4), sticky="ew"
        )

        # Row 6 — Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=6, column=0, columnspan=2, padx=16, pady=(4, 16), sticky="ew")

        ctk.CTkButton(
            btn_frame, text="Cancel", width=90,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"),
            command=self.destroy,
        ).pack(side="left")

        if account:
            ctk.CTkButton(
                btn_frame, text="Delete Account", width=110,
                fg_color="#F44336", hover_color="#D32F2F",
                command=self._on_delete_click,
            ).pack(side="left", padx=8)

        ctk.CTkButton(
            btn_frame, text="Save", width=90,
            command=self._on_save,
        ).pack(side="right")

        self.transient(master)
        self.grab_set()
        self._update_opening_balance_visibility()
        self._center()
        self._name_entry.focus_set()

    def _on_type_change(self, value=None):
        self._update_opening_balance_visibility()

    def _update_opening_balance_visibility(self):
        label = self._type_var.get()
        key = self._LABEL_TO_KEY.get(label, "checking")
        if key in DEBT_ACCOUNT_TYPES:
            self._ob_label.grid()
            self._ob_entry.grid()
            self._ob_hint.grid()
        else:
            self._ob_label.grid_remove()
            self._ob_entry.grid_remove()
            self._ob_hint.grid_remove()

    def _on_save(self):
        name = self._name_var.get().strip()
        desc = self._desc_var.get().strip()
        type_label = self._type_var.get()
        account_type = self._LABEL_TO_KEY.get(type_label, "checking")

        opening_balance = 0.0
        if account_type in DEBT_ACCOUNT_TYPES:
            try:
                opening_balance = float(self._ob_var.get())
            except ValueError:
                self._error_var.set("Opening balance must be a number.")
                return

        try:
            if self._account:
                self._svc.update(self._account.id, name, desc, account_type, opening_balance)
            else:
                self._svc.create(name, desc, account_type, opening_balance)
            self.saved = True
            self.destroy()
        except ValueError as e:
            self._error_var.set(str(e))

    def _on_delete_click(self):
        try:
            self._svc.delete(self._account.id)
            self.saved = True
            if self._on_delete:
                self._on_delete()
            self.destroy()
        except ValueError as e:
            self._error_var.set(str(e))

    def _center(self):
        self.update_idletasks()
        mw = self.master.winfo_x() + self.master.winfo_width() // 2
        mh = self.master.winfo_y() + self.master.winfo_height() // 2
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        self.geometry(f"+{mw - w//2}+{mh - h//2}")
