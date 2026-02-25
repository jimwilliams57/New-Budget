import customtkinter as ctk
from services.reminder_service import Reminder
from utils.constants import SEVERITY_ICONS, SEVERITY_COLORS
from utils.date_helpers import friendly_month, current_month_str


class ReminderDialog(ctk.CTkToplevel):
    """Modal startup dialog listing all reminders with per-row dismiss buttons."""

    def __init__(
        self,
        master,
        reminders: list[Reminder],
        dismissed_reminder_dao=None,
        reminder_service=None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._dismissed_dao = dismissed_reminder_dao
        self._reminder_svc = reminder_service
        self._reminders = list(reminders)

        self.title("Reminders")
        self.geometry("560x420")
        self.resizable(False, True)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        month_label = friendly_month(current_month_str())
        ctk.CTkLabel(
            self,
            text=f"Reminders for {month_label}",
            font=ctk.CTkFont(size=16, weight="bold"),
            pady=12,
        ).grid(row=0, column=0, sticky="ew", padx=16)

        self._scroll = ctk.CTkScrollableFrame(self)
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
        self._scroll.grid_columnconfigure(0, weight=1)

        for i, reminder in enumerate(self._reminders):
            self._add_row(self._scroll, reminder, i)

        ctk.CTkButton(
            self, text="OK, Dismiss All", command=self._dismiss_all,
        ).grid(row=2, column=0, pady=(0, 16), padx=60, sticky="ew")

        self.transient(master)
        self.grab_set()
        self._center()

    def _add_row(self, parent, reminder: Reminder, index: int):
        color = SEVERITY_COLORS.get(reminder.severity, "#888888")
        icon = SEVERITY_ICONS.get(reminder.severity, "·")

        row_frame = ctk.CTkFrame(
            parent,
            fg_color=("gray90", "gray20"),
            corner_radius=6,
        )
        row_frame.grid(row=index, column=0, sticky="ew", pady=3, padx=2)
        row_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            row_frame, text=icon, text_color=color,
            font=ctk.CTkFont(size=18), width=30,
        ).grid(row=0, column=0, rowspan=2, padx=(8, 4), pady=6)

        ctk.CTkLabel(
            row_frame, text=reminder.title,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=color, anchor="w",
        ).grid(row=0, column=1, sticky="ew", padx=(0, 4), pady=(6, 0))

        ctk.CTkLabel(
            row_frame, text=reminder.detail,
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray70"),
            anchor="w", wraplength=380,
        ).grid(row=1, column=1, sticky="ew", padx=(0, 4), pady=(0, 6))

        # Per-row dismiss button (only when DAO is available and reminder has a key)
        if reminder.key and self._dismissed_dao:
            ctk.CTkButton(
                row_frame,
                text="✕",
                width=28,
                height=28,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray80", "gray30"),
                command=lambda r=reminder, f=row_frame: self._dismiss_one(r, f),
            ).grid(row=0, column=2, rowspan=2, padx=(4, 8), pady=6)

    def _dismiss_one(self, reminder: Reminder, row_frame: ctk.CTkFrame):
        """Persist dismissal for this reminder and remove its row."""
        if self._dismissed_dao and self._reminder_svc:
            try:
                expiry = self._reminder_svc.compute_expiry(reminder)
                self._dismissed_dao.dismiss(reminder.key, expiry)
            except Exception:
                pass
        if reminder in self._reminders:
            self._reminders.remove(reminder)
        row_frame.destroy()

    def _dismiss_all(self):
        """Persist dismissals for all remaining reminders, then close."""
        if self._dismissed_dao and self._reminder_svc:
            for reminder in self._reminders:
                if reminder.key:
                    try:
                        expiry = self._reminder_svc.compute_expiry(reminder)
                        self._dismissed_dao.dismiss(reminder.key, expiry)
                    except Exception:
                        pass
        self.destroy()

    def _center(self):
        self.update_idletasks()
        mw = self.master.winfo_x() + self.master.winfo_width() // 2
        mh = self.master.winfo_y() + self.master.winfo_height() // 2
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        self.geometry(f"+{mw - w//2}+{mh - h//2}")
