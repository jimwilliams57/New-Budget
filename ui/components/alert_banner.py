import customtkinter as ctk


class AlertBanner(ctk.CTkFrame):
    """A dismissible colored banner for non-blocking notifications."""

    def __init__(self, master, message: str, color: str = "#2196F3",
                 action_text: str | None = None, action_cmd=None, **kwargs):
        super().__init__(master, fg_color=color, corner_radius=6, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text=message, text_color="white",
            anchor="w", padx=10, pady=6
        ).grid(row=0, column=0, sticky="ew")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=0, column=1, padx=(0, 4))

        if action_text and action_cmd:
            ctk.CTkButton(
                btn_frame, text=action_text, width=60, height=24,
                fg_color="transparent", border_width=1, border_color="white",
                hover_color="#ffffff",
                text_color="white", command=action_cmd,
            ).pack(side="left", padx=2)

        ctk.CTkButton(
            btn_frame, text="✕", width=28, height=24,
            fg_color="transparent",
            hover_color="#ffffff",
            text_color="white",
            command=self.destroy,
        ).pack(side="left")
