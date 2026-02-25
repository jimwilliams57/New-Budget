import json
import customtkinter as ctk
from tkinter import filedialog, messagebox

from database.db_manager import DatabaseManager
from services.data_service import DataService
from utils.app_config import get_db_folder, set_db_folder
from utils.date_helpers import DATE_FORMAT_OPTIONS


class SettingsTab(ctk.CTkFrame):
    """Settings tab: DB folder, export/import, app preferences."""

    def __init__(
        self,
        master,
        db: DatabaseManager,
        data_service: DataService,
        notify_refresh,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._db = db
        self._data_svc = data_service
        self._notify_refresh = notify_refresh

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        self._build_db_folder_section(scroll)
        self._build_export_import_section(scroll)
        self._build_app_settings_section(scroll)

    def refresh(self):
        """Re-read settings from DB and update displayed values."""
        appearance = self._db.get_setting("appearance_mode", "system")
        currency = self._db.get_setting("currency_symbol", "$")
        date_fmt = self._db.get_setting("date_format", "MM/DD/YYYY")

        self._appearance_var.set(appearance.title() if appearance != "system" else "System")
        self._currency_var.set(currency)
        if date_fmt in DATE_FORMAT_OPTIONS:
            self._date_fmt_var.set(date_fmt)

    # ── Section 1: DB folder ──────────────────────────────────────────────────

    def _build_db_folder_section(self, parent):
        section = self._make_section(parent, "Database Folder", row=0)

        ctk.CTkLabel(
            section,
            text="DB files (budget_YYYY.db) are stored in this folder.",
            text_color="gray60",
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=8, pady=(4, 6))

        self._db_folder_var = ctk.StringVar(value=get_db_folder() or "(default: app folder)")
        entry = ctk.CTkEntry(
            section, textvariable=self._db_folder_var,
            state="readonly", width=340,
        )
        entry.grid(row=1, column=0, padx=(8, 4), pady=4, sticky="ew")
        section.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            section, text="Browse…", width=90,
            command=self._browse_db_folder,
        ).grid(row=1, column=1, padx=4)

        ctk.CTkButton(
            section, text="Reset to Default", width=120,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"),
            command=self._reset_db_folder,
        ).grid(row=1, column=2, padx=(4, 8))

        self._db_restart_label = ctk.CTkLabel(
            section,
            text="",
            text_color="#FF9800",
            font=ctk.CTkFont(size=11),
            anchor="w",
        )
        self._db_restart_label.grid(row=2, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 6))

    def _browse_db_folder(self):
        path = filedialog.askdirectory(title="Choose DB folder")
        if path:
            set_db_folder(path)
            self._db_folder_var.set(path)
            self._db_restart_label.configure(
                text="Restart the app for the change to take effect."
            )

    def _reset_db_folder(self):
        set_db_folder(None)
        self._db_folder_var.set("(default: app folder)")
        self._db_restart_label.configure(
            text="Restart the app for the change to take effect."
        )

    # ── Section 2: Export / Import ────────────────────────────────────────────

    def _build_export_import_section(self, parent):
        section = self._make_section(parent, "Export / Import", row=1)

        self._io_status_var = ctk.StringVar()

        btn_frame = ctk.CTkFrame(section, fg_color="transparent")
        btn_frame.grid(row=0, column=0, sticky="w", padx=8, pady=6)

        ctk.CTkButton(
            btn_frame, text="Export as JSON", width=130,
            command=self._export_json,
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_frame, text="Export as CSV ZIP", width=140,
            command=self._export_csv,
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_frame, text="Import JSON…", width=120,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"),
            command=self._import_json,
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_frame, text="Import CSV ZIP…", width=130,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"),
            command=self._import_csv,
        ).pack(side="left", padx=4)

        ctk.CTkLabel(
            section,
            textvariable=self._io_status_var,
            text_color="#4CAF50",
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=8, pady=(0, 6))

    def _export_json(self):
        path = filedialog.asksaveasfilename(
            title="Export as JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            data = self._data_svc.export_json()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            self._io_status_var.set(f"Exported to {path}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    def _export_csv(self):
        path = filedialog.asksaveasfilename(
            title="Export as CSV ZIP",
            defaultextension=".zip",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            self._data_svc.export_csv_zip(path)
            self._io_status_var.set(f"Exported to {path}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    def _import_json(self):
        path = filedialog.askopenfilename(
            title="Import JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Import Failed", f"Could not read file:\n{e}")
            return

        mode = self._ask_import_mode()
        if not mode:
            return

        try:
            stats = self._data_svc.import_json(data, mode)
            self._notify_refresh("full")
            self._io_status_var.set(self._format_stats(stats))
        except Exception as e:
            messagebox.showerror("Import Failed", str(e))

    def _import_csv(self):
        path = filedialog.askopenfilename(
            title="Import CSV ZIP",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")],
        )
        if not path:
            return

        mode = self._ask_import_mode()
        if not mode:
            return

        try:
            stats = self._data_svc.import_csv_zip(path, mode)
            self._notify_refresh("full")
            self._io_status_var.set(self._format_stats(stats))
        except Exception as e:
            messagebox.showerror("Import Failed", str(e))

    def _ask_import_mode(self) -> str | None:
        dlg = _ImportModeDialog(self.winfo_toplevel())
        self.wait_window(dlg)
        return dlg.mode

    def _format_stats(self, stats: dict) -> str:
        parts = [f"{v} {k}" for k, v in stats.items() if v > 0]
        return "Imported: " + ", ".join(parts) if parts else "Nothing new imported."

    # ── Section 3: App settings ───────────────────────────────────────────────

    def _build_app_settings_section(self, parent):
        section = self._make_section(parent, "App Settings", row=2)

        # Appearance
        ctk.CTkLabel(section, text="Appearance:", anchor="e", width=120).grid(
            row=0, column=0, padx=(8, 4), pady=6, sticky="e"
        )
        appearance_raw = self._db.get_setting("appearance_mode", "system")
        appearance_display = appearance_raw.title() if appearance_raw != "system" else "System"
        self._appearance_var = ctk.StringVar(value=appearance_display)
        ctk.CTkComboBox(
            section,
            values=["System", "Light", "Dark"],
            variable=self._appearance_var,
            width=180,
            state="readonly",
        ).grid(row=0, column=1, padx=4, pady=6, sticky="w")

        # Currency symbol
        ctk.CTkLabel(section, text="Currency Symbol:", anchor="e", width=120).grid(
            row=1, column=0, padx=(8, 4), pady=6, sticky="e"
        )
        self._currency_var = ctk.StringVar(
            value=self._db.get_setting("currency_symbol", "$")
        )
        ctk.CTkEntry(section, textvariable=self._currency_var, width=60).grid(
            row=1, column=1, padx=4, pady=6, sticky="w"
        )

        # Date format
        ctk.CTkLabel(section, text="Date Format:", anchor="e", width=120).grid(
            row=2, column=0, padx=(8, 4), pady=6, sticky="e"
        )
        self._date_fmt_var = ctk.StringVar(
            value=self._db.get_setting("date_format", "MM/DD/YYYY")
        )
        ctk.CTkComboBox(
            section,
            values=DATE_FORMAT_OPTIONS,
            variable=self._date_fmt_var,
            width=180,
            state="readonly",
        ).grid(row=2, column=1, padx=4, pady=6, sticky="w")

        ctk.CTkLabel(
            section,
            text="Date format changes take effect on next app restart.",
            text_color="gray60",
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=8)

        # Save button
        ctk.CTkButton(
            section, text="Save Settings", width=140,
            command=self._save_settings,
        ).grid(row=4, column=0, columnspan=2, pady=(10, 8))

        self._settings_status_var = ctk.StringVar()
        ctk.CTkLabel(
            section,
            textvariable=self._settings_status_var,
            text_color="#4CAF50",
            font=ctk.CTkFont(size=11),
        ).grid(row=5, column=0, columnspan=2, pady=(0, 8))

    def _save_settings(self):
        appearance_display = self._appearance_var.get()
        appearance_key = appearance_display.lower()
        currency = self._currency_var.get().strip() or "$"
        date_fmt = self._date_fmt_var.get()

        self._db.set_setting("appearance_mode", appearance_key)
        self._db.set_setting("currency_symbol", currency)
        self._db.set_setting("date_format", date_fmt)
        ctk.set_appearance_mode(appearance_key)
        self._settings_status_var.set("Settings saved.")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _make_section(self, parent, title: str, row: int) -> ctk.CTkFrame:
        """Create a labelled card section and return its inner frame."""
        outer = ctk.CTkFrame(parent, corner_radius=8)
        outer.grid(row=row, column=0, sticky="ew", padx=12, pady=8)
        outer.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            outer,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 8))
        inner.grid_columnconfigure(0, weight=1)
        return inner


class _ImportModeDialog(ctk.CTkToplevel):
    """Small modal asking the user to choose merge or replace import mode."""

    def __init__(self, master):
        super().__init__(master)
        self.mode: str | None = None

        self.title("Choose Import Mode")
        self.resizable(False, False)
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text="How should existing data be handled?",
            font=ctk.CTkFont(size=13),
            wraplength=280,
        ).grid(row=0, column=0, padx=24, pady=(20, 8), sticky="ew")

        ctk.CTkButton(
            self,
            text="Merge – keep existing data",
            command=self._merge,
        ).grid(row=1, column=0, padx=24, pady=4, sticky="ew")

        ctk.CTkButton(
            self,
            text="Replace – wipe and restore",
            fg_color="#F44336",
            hover_color="#D32F2F",
            command=self._replace,
        ).grid(row=2, column=0, padx=24, pady=(4, 8), sticky="ew")

        ctk.CTkButton(
            self,
            text="Cancel",
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            command=self.destroy,
        ).grid(row=3, column=0, padx=24, pady=(0, 16), sticky="ew")

        self.transient(master)
        self.grab_set()
        self._center()

    def _merge(self):
        self.mode = "merge"
        self.destroy()

    def _replace(self):
        self.mode = "replace"
        self.destroy()

    def _center(self):
        self.update_idletasks()
        mw = self.master.winfo_x() + self.master.winfo_width() // 2
        mh = self.master.winfo_y() + self.master.winfo_height() // 2
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        self.geometry(f"+{mw - w//2}+{mh - h//2}")
