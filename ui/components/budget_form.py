import customtkinter as ctk
from services.budget_service import BudgetService
from models.budget import Budget


class BudgetForm(ctk.CTkToplevel):
    """Add or edit a budget limit for a category/month."""

    def __init__(
        self,
        master,
        budget_service: BudgetService,
        month: str,
        budget: Budget | None = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._svc = budget_service
        self._month = month
        self._budget = budget
        self.saved = False

        self.title("Edit Budget" if budget else "New Budget")
        self.resizable(False, False)
        self.grid_columnconfigure(1, weight=1)

        categories = budget_service.get_expense_categories()
        cat_names = [c.name for c in categories]
        self._categories = categories

        r = 0
        # Category selector
        ctk.CTkLabel(self, text="Category:").grid(
            row=r, column=0, padx=(16, 8), pady=(16, 4), sticky="e"
        )
        current_cat = budget.category_name if budget else (cat_names[0] if cat_names else "")
        self._cat_var = ctk.StringVar(value=current_cat)
        self._cat_combo = ctk.CTkComboBox(
            self, values=cat_names, variable=self._cat_var,
            width=200, state="readonly" if not budget else "disabled"
        )
        self._cat_combo.grid(row=r, column=1, padx=(0, 16), pady=(16, 4), sticky="ew")
        r += 1

        # Month (read-only display)
        ctk.CTkLabel(self, text="Month:").grid(
            row=r, column=0, padx=(16, 8), pady=4, sticky="e"
        )
        from utils.date_helpers import friendly_month
        ctk.CTkLabel(self, text=friendly_month(month), anchor="w").grid(
            row=r, column=1, padx=(0, 16), pady=4, sticky="ew"
        )
        r += 1

        # Limit amount
        ctk.CTkLabel(self, text="Limit ($):").grid(
            row=r, column=0, padx=(16, 8), pady=4, sticky="e"
        )
        self._limit_var = ctk.StringVar(
            value=f"{budget.limit_amount:.2f}" if budget else ""
        )
        ctk.CTkEntry(self, textvariable=self._limit_var, width=200).grid(
            row=r, column=1, padx=(0, 16), pady=4, sticky="ew"
        )
        r += 1

        # Error label
        self._error_var = ctk.StringVar()
        ctk.CTkLabel(
            self, textvariable=self._error_var,
            text_color="#F44336", wraplength=280, anchor="w"
        ).grid(row=r, column=0, columnspan=2, padx=16, pady=(0, 4), sticky="ew")
        r += 1

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=r, column=0, columnspan=2, padx=16, pady=(4, 16), sticky="ew")
        ctk.CTkButton(
            btn_frame, text="Cancel", width=90,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"),
            command=self.destroy,
        ).pack(side="left")
        if budget:
            ctk.CTkButton(
                btn_frame, text="Delete", width=80,
                fg_color="#F44336", hover_color="#D32F2F",
                command=self._on_delete,
            ).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="Save", width=90, command=self._on_save).pack(side="right")

        self.transient(master)
        self.grab_set()
        self._center()

    def _on_save(self):
        try:
            limit = float(self._limit_var.get())
        except ValueError:
            self._error_var.set("Invalid amount.")
            return
        cat_name = self._cat_var.get()
        cat = next((c for c in self._categories if c.name == cat_name), None)
        if not cat:
            self._error_var.set("Please select a category.")
            return
        try:
            self._svc.upsert(cat.id, self._month, limit)
            self.saved = True
            self.destroy()
        except ValueError as e:
            self._error_var.set(str(e))

    def _on_delete(self):
        self._svc.delete(self._budget.id)
        self.saved = True
        self.destroy()

    def _center(self):
        self.update_idletasks()
        mw = self.master.winfo_x() + self.master.winfo_width() // 2
        mh = self.master.winfo_y() + self.master.winfo_height() // 2
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        self.geometry(f"+{mw - w//2}+{mh - h//2}")
