import customtkinter as ctk
from tkinter import colorchooser
from services.category_service import CategoryService
from models.category import Category


class CategoryForm(ctk.CTkToplevel):
    """Add or edit a category."""

    TYPES = ["expense", "income", "both"]

    def __init__(
        self,
        master,
        category_service: CategoryService,
        category: Category | None = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._svc = category_service
        self._category = category
        self.saved = False

        self.title("Edit Category" if category else "New Category")
        self.resizable(False, False)
        self.grid_columnconfigure(1, weight=1)

        r = 0

        # Name
        ctk.CTkLabel(self, text="Name:").grid(
            row=r, column=0, padx=(16, 8), pady=(16, 4), sticky="e"
        )
        self._name_var = ctk.StringVar(value=category.name if category else "")
        ctk.CTkEntry(self, textvariable=self._name_var, width=220).grid(
            row=r, column=1, padx=(0, 16), pady=(16, 4), sticky="ew"
        )
        r += 1

        # Type
        ctk.CTkLabel(self, text="Type:").grid(
            row=r, column=0, padx=(16, 8), pady=4, sticky="e"
        )
        current_type = category.type if category else "expense"
        self._type_var = ctk.StringVar(value=current_type)
        ctk.CTkComboBox(
            self, values=self.TYPES, variable=self._type_var,
            width=220, state="readonly",
        ).grid(row=r, column=1, padx=(0, 16), pady=4, sticky="ew")
        r += 1

        # Color
        ctk.CTkLabel(self, text="Color:").grid(
            row=r, column=0, padx=(16, 8), pady=4, sticky="e"
        )
        color_row = ctk.CTkFrame(self, fg_color="transparent")
        color_row.grid(row=r, column=1, padx=(0, 16), pady=4, sticky="ew")

        self._color_var = ctk.StringVar(value=category.color_hex if category else "#888888")
        self._color_entry = ctk.CTkEntry(color_row, textvariable=self._color_var, width=100)
        self._color_entry.pack(side="left")
        self._color_entry.bind("<FocusOut>", self._sync_swatch)

        self._swatch = ctk.CTkLabel(
            color_row, text="", width=32, height=24, corner_radius=4,
            fg_color=self._color_var.get(),
        )
        self._swatch.pack(side="left", padx=(8, 0))

        ctk.CTkButton(
            color_row, text="Pick", width=60,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"),
            command=self._pick_color,
        ).pack(side="left", padx=(8, 0))
        r += 1

        # System notice
        if category and category.is_system:
            ctk.CTkLabel(
                self, text="System category — cannot be deleted.",
                text_color="gray60", anchor="w",
            ).grid(row=r, column=0, columnspan=2, padx=16, pady=(0, 4), sticky="ew")
            r += 1

        # Error
        self._error_var = ctk.StringVar()
        ctk.CTkLabel(
            self, textvariable=self._error_var,
            text_color="#F44336", wraplength=300, anchor="w",
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
        if category and not category.is_system:
            ctk.CTkButton(
                btn_frame, text="Delete", width=80,
                fg_color="#F44336", hover_color="#D32F2F",
                command=self._on_delete,
            ).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="Save", width=90, command=self._on_save).pack(side="right")

        self.transient(master)
        self.grab_set()
        self._center()

    def _pick_color(self):
        result = colorchooser.askcolor(
            color=self._color_var.get(), parent=self, title="Pick Category Color"
        )
        if result and result[1]:
            self._color_var.set(result[1])
            self._swatch.configure(fg_color=result[1])

    def _sync_swatch(self, _event=None):
        color = self._color_var.get().strip()
        if color.startswith("#") and len(color) in (4, 7):
            try:
                self._swatch.configure(fg_color=color)
            except Exception:
                pass

    def _on_save(self):
        name = self._name_var.get().strip()
        type_ = self._type_var.get()
        color = self._color_var.get().strip()
        if not color.startswith("#"):
            color = "#" + color
        try:
            if self._category:
                self._svc.update(self._category.id, name, type_, color)
            else:
                self._svc.create(name, type_, color)
            self.saved = True
            self.destroy()
        except ValueError as e:
            self._error_var.set(str(e))

    def _on_delete(self):
        try:
            self._svc.delete(self._category.id)
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
