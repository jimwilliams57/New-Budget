import customtkinter as ctk
from tkcalendar import Calendar
import tkinter as tk
from tkinter import ttk
from utils.date_helpers import (
    parse_date, format_date, format_display_date, parse_display_date,
)
from datetime import date


class DatePickerWidget(ctk.CTkFrame):
    """Reusable date picker: CTkEntry (in display format) + calendar popup button.

    .get() always returns a YYYY-MM-DD string for storage.
    .set(date_str) accepts YYYY-MM-DD and converts to the display format.
    """

    def __init__(
        self,
        master,
        initial_date: str | None = None,
        date_format: str = "MM/DD/YYYY",
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)

        self._date_format = date_format
        self._popup: ctk.CTkToplevel | None = None

        # Show display format in the entry; always empty if initial_date is falsy
        if initial_date:
            display_val = format_display_date(initial_date, date_format)
        else:
            display_val = ""

        self._var = tk.StringVar(value=display_val)

        self._entry = ctk.CTkEntry(self, textvariable=self._var, width=110)
        self._entry.grid(row=0, column=0, sticky="ew")
        self._entry.bind("<FocusOut>", self._on_focus_out)
        self._entry.bind("<Return>", self._on_focus_out)

        self._btn = ctk.CTkButton(
            self, text="📅", width=32, command=self._open_popup
        )
        self._btn.grid(row=0, column=1, padx=(4, 0))

    def get(self) -> str:
        """Return date as YYYY-MM-DD for storage, or '' if empty/invalid."""
        raw = self._var.get().strip()
        if not raw:
            return ""
        d = parse_display_date(raw, self._date_format)
        if d is None:
            normalized = raw.replace("/", "-").replace(".", "-")
            d = parse_date(normalized)
        return format_date(d) if d else raw

    def set(self, date_str: str):
        """Accept a YYYY-MM-DD string and display it in the chosen format."""
        if date_str:
            d = parse_date(date_str)
            if d:
                self._var.set(format_display_date(format_date(d), self._date_format))
            else:
                self._var.set(date_str)
        else:
            self._var.set("")
        self._reset_border()

    def is_valid(self) -> bool:
        raw = self._var.get().strip()
        if not raw:
            return False
        d = parse_display_date(raw, self._date_format)
        if d is None:
            normalized = raw.replace("/", "-").replace(".", "-")
            d = parse_date(normalized)
        return d is not None

    def _on_focus_out(self, _event=None):
        raw = self._var.get().strip()
        if not raw:
            self._reset_border()
            return
        d = parse_display_date(raw, self._date_format)
        if d is None:
            normalized = raw.replace("/", "-").replace(".", "-")
            d = parse_date(normalized)
        if d:
            self._var.set(format_display_date(format_date(d), self._date_format))
            self._reset_border()
        else:
            self._entry.configure(border_color="#F44336")

    def _reset_border(self):
        self._entry.configure(border_color=("gray65", "gray35"))

    def _open_popup(self):
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
            self._popup = None
            return

        popup = ctk.CTkToplevel(self)
        popup.overrideredirect(True)
        popup.resizable(False, False)
        self._popup = popup

        # Theme the calendar to match CTk appearance
        mode = ctk.get_appearance_mode()
        style = ttk.Style(popup)
        if mode == "Dark":
            bg = "#2b2b2b"
            fg = "#ffffff"
            sel_bg = "#1f6aa5"
        else:
            bg = "#ffffff"
            fg = "#000000"
            sel_bg = "#1f6aa5"

        style.theme_use("default")
        style.configure(
            "Calendar.Treeview",
            background=bg, foreground=fg,
            fieldbackground=bg,
        )

        # Parse the current display value to position the calendar
        raw = self._var.get().strip()
        current = parse_display_date(raw, self._date_format) if raw else None
        if current is None and raw:
            normalized = raw.replace("/", "-").replace(".", "-")
            current = parse_date(normalized)
        if current is None:
            current = date.today()

        # Calendar always uses yyyy-mm-dd internally; we format the result ourselves
        cal = Calendar(
            popup,
            selectmode="day",
            year=current.year,
            month=current.month,
            day=current.day,
            date_pattern="yyyy-mm-dd",
            background=bg,
            foreground=fg,
            headersbackground=bg,
            headersforeground=fg,
            selectbackground=sel_bg,
            weekendbackground=bg,
            weekendforeground=fg,
            othermonthforeground="gray60",
            bordercolor=bg,
        )
        cal.pack(padx=4, pady=4)
        cal.bind("<<CalendarSelected>>", lambda e: self._on_date_selected(cal, popup))

        # Position below the entry
        self._entry.update_idletasks()
        x = self._entry.winfo_rootx()
        y = self._entry.winfo_rooty() + self._entry.winfo_height() + 2
        popup.geometry(f"+{x}+{y}")

        popup.bind("<FocusOut>", lambda e: self._maybe_close(popup))

    def _on_date_selected(self, cal, popup):
        # cal always returns yyyy-mm-dd; convert to display format for the entry
        iso = cal.get_date()
        d = parse_date(iso)
        if d:
            self._var.set(format_display_date(format_date(d), self._date_format))
        else:
            self._var.set(iso)
        self._reset_border()
        popup.destroy()
        self._popup = None

    def _maybe_close(self, popup):
        try:
            focused = popup.focus_get()
            if focused is None or not str(focused).startswith(str(popup)):
                popup.destroy()
                self._popup = None
        except Exception:
            pass
