import customtkinter as ctk


class ConfirmDialog(ctk.CTkToplevel):
    """Simple yes/no confirmation dialog. Returns result via .result attribute."""

    def __init__(self, master, title: str, message: str, **kwargs):
        super().__init__(master, **kwargs)
        self.title(title)
        self.result = False
        self.resizable(False, False)

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text=message, wraplength=360, justify="left", padx=20, pady=16
        ).grid(row=0, column=0, sticky="ew")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=1, column=0, pady=(0, 16), padx=20, sticky="e")

        ctk.CTkButton(
            btn_frame, text="Cancel", width=90,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"),
            command=self._on_cancel,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="Confirm", width=90,
            fg_color="#F44336", hover_color="#D32F2F",
            command=self._on_confirm,
        ).pack(side="left")

        self.transient(master)
        self.grab_set()
        self._center()
        self.wait_window()

    def _center(self):
        self.update_idletasks()
        mw = self.master.winfo_x() + self.master.winfo_width() // 2
        mh = self.master.winfo_y() + self.master.winfo_height() // 2
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{mw - w//2}+{mh - h//2}")

    def _on_confirm(self):
        self.result = True
        self.destroy()

    def _on_cancel(self):
        self.result = False
        self.destroy()
