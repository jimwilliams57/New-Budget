import threading
import customtkinter as ctk
import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from services.forecast_service import ForecastService
from services.account_service import AccountService
from utils.currency import format_currency


class ForecastTab(ctk.CTkFrame):
    def __init__(
        self,
        master,
        forecast_service: ForecastService,
        account_service: AccountService,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._forecast_svc = forecast_service
        self._acct_svc = account_service

        accounts = account_service.get_all()
        self._accounts = accounts
        self._acct_names = ["All Accounts"] + [a.name for a in accounts]
        self._acct_var = ctk.StringVar(value="All Accounts")
        self._source_var = ctk.StringVar(value="Recurring + History")
        self._view_var = ctk.StringVar(value="Monthly")
        self._load_gen = 0

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=1)

        self._build_toolbar()
        self._build_chart_area()
        self._build_table()
        self.after(100, self._load)

    def refresh(self):
        self._load()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _get_account_id(self):
        name = self._acct_var.get()
        if name == "All Accounts":
            return None
        acct = next((a for a in self._accounts if a.name == name), None)
        return acct.id if acct else None

    def _get_source(self) -> int:
        return {"Recurring Only": 1, "Recurring + Budgets": 2, "Recurring + History": 3}.get(
            self._source_var.get(), 3
        )

    def _style_ax(self, ax, fig):
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg = "#2b2b2b" if is_dark else "#e4e4e4"
        fg = "#aaaaaa" if is_dark else "#444444"
        fig.patch.set_facecolor(bg)
        ax.set_facecolor(bg)
        ax.tick_params(colors=fg, labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor(fg)

    # ── Layout ───────────────────────────────────────────────────────────────

    def _build_toolbar(self):
        bar = ctk.CTkFrame(self, fg_color=("gray88", "gray18"), corner_radius=8)
        bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))

        ctk.CTkLabel(bar, text="Account:").pack(side="left", padx=(12, 4), pady=8)
        ctk.CTkComboBox(
            bar, values=self._acct_names, variable=self._acct_var,
            width=160, state="readonly",
            command=lambda _: self._load(),
        ).pack(side="left", padx=(0, 16))

        ctk.CTkLabel(bar, text="Source:").pack(side="left", padx=(0, 4))
        ctk.CTkSegmentedButton(
            bar,
            values=["Recurring Only", "Recurring + Budgets", "Recurring + History"],
            variable=self._source_var,
            command=lambda _: self._load(),
        ).pack(side="left", padx=(0, 16))

        ctk.CTkLabel(bar, text="View:").pack(side="left", padx=(0, 4))
        ctk.CTkSegmentedButton(
            bar,
            values=["Monthly", "Annual"],
            variable=self._view_var,
            command=lambda _: self._load(),
        ).pack(side="left", padx=(0, 8))

    def _build_chart_area(self):
        outer = ctk.CTkFrame(self, fg_color=("gray90", "gray20"), corner_radius=8)
        outer.grid(row=1, column=0, sticky="ew", padx=8, pady=8)
        outer.grid_columnconfigure(0, weight=1)

        self._chart_title = ctk.CTkLabel(
            outer, text="Forecast",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self._chart_title.pack(pady=(10, 0))

        # Legend
        legend_frame = ctk.CTkFrame(outer, fg_color="transparent")
        legend_frame.pack()
        for color, label in (("#4CAF50", "Income"), ("#F44336", "Expense")):
            tk.Label(legend_frame, bg=color, width=2).pack(side="left", padx=(8, 2))
            ctk.CTkLabel(legend_frame, text=label, font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 8))

        self._chart_fig = Figure(figsize=(8, 2.8), dpi=80, tight_layout=True)
        self._chart_ax = self._chart_fig.add_subplot(111)
        self._chart_mpl = FigureCanvasTkAgg(self._chart_fig, master=outer)
        self._chart_mpl.get_tk_widget().pack(fill="x", expand=True, padx=8, pady=(4, 8))

    def _build_table(self):
        outer = ctk.CTkFrame(self, fg_color=("gray90", "gray20"), corner_radius=8)
        outer.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(1, weight=1)

        # Header row
        header = ctk.CTkFrame(outer, fg_color=("gray80", "gray25"), corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 0))
        for col, (text, w) in enumerate([("Period", 120), ("Income", 120), ("Expense", 120), ("Net", 120)]):
            header.grid_columnconfigure(col, weight=1, minsize=w)
            ctk.CTkLabel(
                header, text=text,
                font=ctk.CTkFont(weight="bold"),
                anchor="center",
            ).grid(row=0, column=col, padx=4, pady=6, sticky="ew")

        self._table_scroll = ctk.CTkScrollableFrame(outer, fg_color="transparent")
        self._table_scroll.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        for col in range(4):
            self._table_scroll.grid_columnconfigure(col, weight=1, minsize=120)

    # ── Data loading ─────────────────────────────────────────────────────────

    def _load(self):
        self._load_gen += 1
        gen = self._load_gen
        account_id = self._get_account_id()
        source = self._get_source()
        view = self._view_var.get()

        def fetch():
            try:
                if view == "Monthly":
                    data = self._forecast_svc.get_monthly_forecast(account_id, source)
                else:
                    data = self._forecast_svc.get_annual_forecast(account_id, source)
            except Exception:
                data = []
            self.after(0, lambda: self._on_data_ready(gen, data, view))

        threading.Thread(target=fetch, daemon=True).start()

    def _on_data_ready(self, gen: int, data: list[dict], view: str):
        if gen != self._load_gen:
            return  # superseded by a newer load
        if not self.winfo_exists():
            return
        if view == "Monthly":
            self._chart_title.configure(text="Monthly Forecast (through Dec next year)")
            self._draw_bar_chart(data, "Monthly")
            self._populate_table(data, "Monthly")
        else:
            self._chart_title.configure(text="Annual Forecast (10 years)")
            self._draw_bar_chart(data, "Annual")
            self._populate_table(data, "Annual")

    # ── Chart drawing ─────────────────────────────────────────────────────────

    def _draw_bar_chart(self, data: list[dict], mode: str):
        ax = self._chart_ax
        ax.clear()
        self._style_ax(ax, self._chart_fig)

        if not data:
            ax.text(0.5, 0.5, "No data", ha="center", va="center",
                    transform=ax.transAxes, color="gray")
            self._chart_mpl.draw_idle()
            return

        if mode == "Monthly":
            labels = [d["month"][5:] for d in data]
        else:
            labels = [str(d["year"]) for d in data]
        incomes  = [d.get("income",  0) for d in data]
        expenses = [d.get("expense", 0) for d in data]

        x = list(range(len(labels)))
        w = 0.35
        ax.bar([i - w / 2 for i in x], incomes,  w, color="#4CAF50")
        ax.bar([i + w / 2 for i in x], expenses, w, color="#F44336")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45 if len(labels) > 12 else 0, ha="right")
        ax.yaxis.set_major_formatter(
            lambda v, _: f"{v/1000:.0f}k" if abs(v) >= 1000 else f"{v:.0f}"
        )
        self._chart_mpl.draw_idle()

    # ── Table population ─────────────────────────────────────────────────────

    def _populate_table(self, data: list[dict], mode: str):
        for w in self._table_scroll.winfo_children():
            w.destroy()

        for row_idx, d in enumerate(data):
            bg = ("gray85", "gray22") if row_idx % 2 == 0 else ("gray90", "gray18")

            if mode == "Monthly":
                period_label = d["month"]
            else:
                period_label = str(d["year"])

            net = d["net"]
            net_color = "#4CAF50" if net >= 0 else "#F44336"

            for col, (text, color) in enumerate([
                (period_label, None),
                (format_currency(d["income"]), "#4CAF50"),
                (format_currency(d["expense"]), "#F44336"),
                (format_currency(net), net_color),
            ]):
                ctk.CTkLabel(
                    self._table_scroll,
                    text=text,
                    text_color=color or ("gray10", "gray90"),
                    fg_color=bg,
                    anchor="center",
                    corner_radius=0,
                ).grid(row=row_idx, column=col, padx=1, pady=1, sticky="ew")


