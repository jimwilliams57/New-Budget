import customtkinter as ctk
from services.category_service import CategoryService
from ui.components.category_form import CategoryForm
from ui.components.confirm_dialog import ConfirmDialog


class CategoriesTab(ctk.CTkFrame):
    def __init__(
        self,
        master,
        category_service: CategoryService,
        notify_refresh,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._svc = category_service
        self._notify_refresh = notify_refresh

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
            bar, text="Expense Categories",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="left", padx=(12, 16), pady=8)

        ctk.CTkButton(
            bar, text="+ Add Category", command=self._open_add,
        ).pack(side="left", padx=4, pady=6)

    def _build_list(self):
        self._scroll = ctk.CTkScrollableFrame(self)
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self._scroll.grid_columnconfigure(0, weight=1)

    def _load(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        categories = self._svc.get_all()
        if not categories:
            ctk.CTkLabel(
                self._scroll,
                text="No categories found.",
                text_color="gray60",
            ).grid(row=0, column=0, pady=40)
            return

        # Column headers
        hdr = ctk.CTkFrame(self._scroll, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=4, pady=(0, 2))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr, text="Color", width=44, anchor="center", text_color="gray60",
                     font=ctk.CTkFont(size=11)).grid(row=0, column=0, padx=(4, 0))
        ctk.CTkLabel(hdr, text="Name", anchor="w", text_color="gray60",
                     font=ctk.CTkFont(size=11)).grid(row=0, column=1, padx=8, sticky="w")
        ctk.CTkLabel(hdr, text="Type", width=70, anchor="center", text_color="gray60",
                     font=ctk.CTkFont(size=11)).grid(row=0, column=2)
        ctk.CTkLabel(hdr, text="", width=130).grid(row=0, column=3)  # button placeholder

        for idx, cat in enumerate(categories):
            self._add_row(idx + 1, cat)

    def _add_row(self, idx, cat):
        row = ctk.CTkFrame(
            self._scroll, fg_color=("gray90", "gray20"), corner_radius=8
        )
        row.grid(row=idx, column=0, sticky="ew", padx=4, pady=3)
        row.grid_columnconfigure(1, weight=1)

        # Color swatch
        swatch = ctk.CTkLabel(
            row, text="", width=28, height=28, corner_radius=4,
            fg_color=cat.color_hex,
        )
        swatch.grid(row=0, column=0, padx=(10, 0), pady=8)

        # Name + optional system badge
        name_frame = ctk.CTkFrame(row, fg_color="transparent")
        name_frame.grid(row=0, column=1, padx=8, sticky="w")
        ctk.CTkLabel(
            name_frame, text=cat.name,
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
        ).pack(side="left")
        if cat.is_system:
            ctk.CTkLabel(
                name_frame, text="system",
                text_color="gray60", font=ctk.CTkFont(size=10),
            ).pack(side="left", padx=(6, 0))

        # Type badge
        type_colors = {
            "expense": "#F44336",
            "income": "#4CAF50",
            "both": "#2196F3",
        }
        badge_color = type_colors.get(cat.type, "#888888")
        ctk.CTkLabel(
            row, text=cat.type, width=70, anchor="center",
            text_color=badge_color,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).grid(row=0, column=2, padx=4)

        # Buttons
        btn_frame = ctk.CTkFrame(row, fg_color="transparent")
        btn_frame.grid(row=0, column=3, padx=(4, 10), pady=6)

        ctk.CTkButton(
            btn_frame, text="Edit", width=60, height=26,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"),
            command=lambda c=cat: self._open_edit(c),
        ).pack(side="left", padx=(0, 4))

        del_btn = ctk.CTkButton(
            btn_frame, text="Delete", width=65, height=26,
            fg_color="#F44336", hover_color="#D32F2F",
            command=lambda c=cat: self._on_delete(c),
        )
        if cat.is_system:
            del_btn.configure(state="disabled", fg_color="gray50")
        del_btn.pack(side="left")

    def _open_add(self):
        form = CategoryForm(self.winfo_toplevel(), self._svc)
        self.wait_window(form)
        if form.saved:
            self._notify_refresh("category")

    def _open_edit(self, cat):
        form = CategoryForm(self.winfo_toplevel(), self._svc, category=cat)
        self.wait_window(form)
        if form.saved:
            self._notify_refresh("category")

    def _on_delete(self, cat):
        dlg = ConfirmDialog(
            self.winfo_toplevel(),
            title="Delete Category",
            message=f"Delete '{cat.name}'? Existing transactions will keep their category label, but it won't appear in new dropdowns.",
        )
        if dlg.result:
            try:
                self._svc.delete(cat.id)
                self._notify_refresh("category")
            except ValueError as e:
                # show inline error - just reload to reflect current state
                self._load()
