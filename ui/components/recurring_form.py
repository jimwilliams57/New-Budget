import customtkinter as ctk
from services.recurring_service import RecurringService
from services.account_service import AccountService
from database.category_dao import CategoryDAO
from models.recurring_rule import RecurringRule
from ui.components.date_picker import DatePickerWidget
from utils.date_helpers import today_str
from utils.constants import FREQUENCIES, DAYS_OF_WEEK, WEEK_INTERVALS


class RecurringForm(ctk.CTkToplevel):
    """Add or edit a recurring rule."""

    def __init__(
        self,
        master,
        recurring_service: RecurringService,
        account_service: AccountService,
        category_dao: CategoryDAO,
        rule: RecurringRule | None = None,
        date_format: str = "MM/DD/YYYY",
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._svc = recurring_service
        self._acct_svc = account_service
        self._cat_dao = category_dao
        self._rule = rule
        self._date_format = date_format
        self.saved = False

        self.title("Edit Recurring Rule" if rule else "New Recurring Rule")
        self.resizable(False, False)
        self.grid_columnconfigure(1, weight=1)

        self._accounts = account_service.get_all()
        account_names = [a.name for a in self._accounts]
        self._all_cats = category_dao.get_all()

        r = 0

        # Name
        self._add_label("Name:", r)
        self._name_var = ctk.StringVar(value=rule.name if rule else "")
        ctk.CTkEntry(self, textvariable=self._name_var, width=220).grid(
            row=r, column=1, padx=(0, 16), pady=4, sticky="ew"
        )
        r += 1

        # Type
        self._add_label("Type:", r)
        self._type_var = ctk.StringVar(value=rule.type if rule else "expense")
        type_frame = ctk.CTkFrame(self, fg_color="transparent")
        type_frame.grid(row=r, column=1, padx=(0, 16), pady=4, sticky="w")
        for t in ("income", "expense"):
            ctk.CTkRadioButton(
                type_frame, text=t.title(),
                variable=self._type_var, value=t,
                command=self._on_type_change,
            ).pack(side="left", padx=4)
        r += 1

        # Amount
        self._add_label("Amount:", r)
        self._amount_var = ctk.StringVar(value=f"{rule.amount:.2f}" if rule else "")
        ctk.CTkEntry(self, textvariable=self._amount_var, width=220).grid(
            row=r, column=1, padx=(0, 16), pady=4, sticky="ew"
        )
        r += 1

        # Account
        self._add_label("Account:", r)
        current_acct = ""
        if rule:
            current_acct = rule.account_name
        elif self._accounts:
            current_acct = self._accounts[0].name
        self._acct_var = ctk.StringVar(value=current_acct)
        ctk.CTkComboBox(
            self, values=account_names,
            variable=self._acct_var, width=220, state="readonly"
        ).grid(row=r, column=1, padx=(0, 16), pady=4, sticky="ew")
        r += 1

        # Category
        self._add_label("Category:", r)
        init_type = rule.type if rule else "expense"
        self._cats = self._get_cats(init_type)
        cat_names = [c.name for c in self._cats]
        current_cat = rule.category_name if rule else (cat_names[0] if cat_names else "")
        self._cat_var = ctk.StringVar(value=current_cat)
        self._cat_combo = ctk.CTkComboBox(
            self, values=cat_names, variable=self._cat_var,
            width=220, state="readonly"
        )
        self._cat_combo.grid(row=r, column=1, padx=(0, 16), pady=4, sticky="ew")
        r += 1

        # Description
        self._add_label("Description:", r)
        self._desc_var = ctk.StringVar(value=rule.description if rule else "")
        ctk.CTkEntry(self, textvariable=self._desc_var, width=220).grid(
            row=r, column=1, padx=(0, 16), pady=4, sticky="ew"
        )
        r += 1

        # Frequency
        self._add_label("Frequency:", r)
        self._freq_var = ctk.StringVar(value=rule.frequency if rule else "monthly")
        self._freq_combo = ctk.CTkComboBox(
            self, values=FREQUENCIES, variable=self._freq_var,
            width=220, state="readonly",
            command=self._on_freq_change,
        )
        self._freq_combo.grid(row=r, column=1, padx=(0, 16), pady=4, sticky="ew")
        r += 1

        # Day fields (dynamic)
        self._day_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._day_frame.grid(row=r, column=0, columnspan=2, padx=16, pady=2, sticky="ew")
        self._day_frame.grid_columnconfigure(1, weight=1)
        r += 1
        dom_init = ""
        if rule and rule.day_of_month is not None:
            dom_init = "Last" if rule.day_of_month == 0 else str(rule.day_of_month)
        self._dom_var = ctk.StringVar(value=dom_init)
        self._dow_var = ctk.StringVar(value=DAYS_OF_WEEK[rule.day_of_week] if rule and rule.day_of_week is not None else "Mon")
        self._moy_var = ctk.StringVar(value=str(rule.month_of_year or "") if rule else "")
        self._refresh_day_fields()

        # Start date
        self._add_label("Start Date:", r)
        self._start_picker = DatePickerWidget(
            self,
            initial_date=rule.start_date if rule else today_str(),
            date_format=self._date_format,
        )
        self._start_picker.grid(row=r, column=1, padx=(0, 16), pady=4, sticky="w")
        r += 1

        # End date
        self._add_label("End Date:", r)
        self._end_picker = DatePickerWidget(
            self,
            initial_date=rule.end_date if rule else "",
            date_format=self._date_format,
        )
        self._end_picker.grid(row=r, column=1, padx=(0, 16), pady=4, sticky="w")
        ctk.CTkLabel(self, text="(optional)", text_color="gray60", font=ctk.CTkFont(size=11)).grid(
            row=r, column=1, padx=(160, 0), pady=4, sticky="w"
        )
        r += 1

        # Error + buttons
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
        if rule:
            ctk.CTkButton(
                btn_frame, text="Delete", width=80,
                fg_color="#F44336", hover_color="#D32F2F",
                command=self._on_delete,
            ).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="Save", width=90, command=self._on_save).pack(side="right")

        self.transient(master)
        self.grab_set()
        self._center()

    def _add_label(self, text, row):
        ctk.CTkLabel(self, text=text).grid(
            row=row, column=0, padx=(16, 8), pady=4, sticky="e"
        )

    def _get_cats(self, type_: str):
        return [c for c in self._all_cats if c.type in (type_, "both")]

    def _on_type_change(self):
        t = self._type_var.get()
        self._cats = self._get_cats(t)
        cat_names = [c.name for c in self._cats]
        self._cat_combo.configure(values=cat_names)
        if cat_names:
            self._cat_var.set(cat_names[0])
            self._cat_combo.set(cat_names[0])

    def _on_freq_change(self, value=None):
        self._refresh_day_fields()

    def _refresh_day_fields(self):
        for w in self._day_frame.winfo_children():
            w.destroy()

        freq = self._freq_var.get()
        if freq == "monthly":
            ctk.CTkLabel(self._day_frame, text="Day of Month:").grid(
                row=0, column=0, padx=(0, 8), sticky="e"
            )
            dom_choices = [str(i) for i in range(1, 29)] + ["Last"]
            ctk.CTkComboBox(
                self._day_frame, values=dom_choices,
                variable=self._dom_var, width=80, state="readonly",
            ).grid(row=0, column=1, sticky="w")

        elif freq in WEEK_INTERVALS:
            ctk.CTkLabel(self._day_frame, text="Day of Week:").grid(
                row=0, column=0, padx=(0, 8), sticky="e"
            )
            ctk.CTkComboBox(
                self._day_frame, values=DAYS_OF_WEEK,
                variable=self._dow_var, width=120, state="readonly"
            ).grid(row=0, column=1, sticky="w")

        elif freq == "yearly":
            ctk.CTkLabel(self._day_frame, text="Month:").grid(
                row=0, column=0, padx=(0, 8), sticky="e"
            )
            ctk.CTkEntry(
                self._day_frame, textvariable=self._moy_var, width=60,
                placeholder_text="1-12",
            ).grid(row=0, column=1, sticky="w")
            ctk.CTkLabel(self._day_frame, text="Day:").grid(
                row=0, column=2, padx=(12, 8), sticky="e"
            )
            dom_choices = [str(i) for i in range(1, 29)] + ["Last"]
            ctk.CTkComboBox(
                self._day_frame, values=dom_choices,
                variable=self._dom_var, width=80, state="readonly",
            ).grid(row=0, column=3, sticky="w")

    def _on_save(self):
        name = self._name_var.get().strip()
        type_ = self._type_var.get()
        desc = self._desc_var.get().strip()
        freq = self._freq_var.get()

        try:
            amount = float(self._amount_var.get())
        except ValueError:
            self._error_var.set("Invalid amount.")
            return

        if not self._start_picker.is_valid():
            self._error_var.set("Invalid start date.")
            return
        start_date = self._start_picker.get()

        end_date = None
        if self._end_picker.get():
            if not self._end_picker.is_valid():
                self._error_var.set("Invalid end date.")
                return
            end_date = self._end_picker.get()

        acct_name = self._acct_var.get()
        acct = next((a for a in self._accounts if a.name == acct_name), None)
        if not acct:
            self._error_var.set("Please select an account.")
            return

        cat_name = self._cat_var.get()
        cat = next((c for c in self._cats if c.name == cat_name), None)
        if not cat:
            self._error_var.set("Please select a category.")
            return

        # Day fields
        day_of_month = None
        day_of_week = None
        month_of_year = None

        if freq == "monthly":
            dom_str = self._dom_var.get()
            if dom_str == "Last":
                day_of_month = 0
            elif dom_str:
                try:
                    day_of_month = int(dom_str)
                    if not (1 <= day_of_month <= 28):
                        raise ValueError
                except ValueError:
                    self._error_var.set("Day of month must be 1-28 or Last.")
                    return
            else:
                day_of_month = None

        elif freq in WEEK_INTERVALS:
            dow_str = self._dow_var.get()
            day_of_week = DAYS_OF_WEEK.index(dow_str) if dow_str in DAYS_OF_WEEK else 0

        elif freq == "yearly":
            try:
                month_of_year = int(self._moy_var.get()) if self._moy_var.get() else None
                if month_of_year and not (1 <= month_of_year <= 12):
                    raise ValueError
            except ValueError:
                self._error_var.set("Month must be 1-12.")
                return
            dom_str = self._dom_var.get()
            if dom_str == "Last":
                day_of_month = 0
            elif dom_str:
                try:
                    day_of_month = int(dom_str)
                    if not (1 <= day_of_month <= 28):
                        raise ValueError
                except ValueError:
                    self._error_var.set("Day must be 1-28 or Last.")
                    return
            else:
                day_of_month = None

        try:
            if self._rule:
                self._svc.update(
                    self._rule.id, name, type_, amount, acct.id, cat.id,
                    desc, freq, start_date, day_of_month, day_of_week,
                    month_of_year, end_date, is_active=self._rule.is_active,
                )
            else:
                self._svc.create(
                    name, type_, amount, acct.id, cat.id, desc,
                    freq, start_date, day_of_month, day_of_week,
                    month_of_year, end_date,
                )
            self.saved = True
            self.destroy()
        except ValueError as e:
            self._error_var.set(str(e))

    def _on_delete(self):
        self._svc.delete(self._rule.id)
        self.saved = True
        self.destroy()

    def _center(self):
        self.update_idletasks()
        mw = self.master.winfo_x() + self.master.winfo_width() // 2
        mh = self.master.winfo_y() + self.master.winfo_height() // 2
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        self.geometry(f"+{mw - w//2}+{mh - h//2}")
