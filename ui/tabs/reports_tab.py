import customtkinter as ctk
import tkinter as tk
import csv
import os
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from services.report_service import ReportService
from services.account_service import AccountService
from utils.currency import format_currency
from utils.date_helpers import current_month_str, friendly_month


class ReportsTab(ctk.CTkFrame):
    def __init__(
        self,
        master,
        report_service: ReportService,
        account_service: AccountService,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._report_svc = report_service
        self._acct_svc = account_service

        accounts = account_service.get_all()
        self._accounts = accounts
        self._acct_names = ["All Accounts"] + [a.name for a in accounts]
        self._acct_var = ctk.StringVar(value="All Accounts")

        self._month_var = ctk.StringVar(value=current_month_str())

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_toolbar()
        self._build_summary()
        self._build_charts()
        self._load()

    def refresh(self):
        self._load()

    def _build_toolbar(self):
        bar = ctk.CTkFrame(self, fg_color=("gray88", "gray18"), corner_radius=8)
        bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))

        ctk.CTkLabel(bar, text="Account:").pack(side="left", padx=(12, 4), pady=8)
        ctk.CTkComboBox(
            bar, values=self._acct_names, variable=self._acct_var,
            width=160, state="readonly",
            command=lambda _: self._load(),
        ).pack(side="left", padx=(0, 12))

        ctk.CTkLabel(bar, text="Month:").pack(side="left", padx=(0, 4))
        ctk.CTkButton(bar, text="◀", width=28, command=self._prev_month).pack(side="left")
        ctk.CTkLabel(bar, textvariable=self._month_var, width=100, anchor="center").pack(side="left", padx=4)
        ctk.CTkButton(bar, text="▶", width=28, command=self._next_month).pack(side="left", padx=(0, 12))

        ctk.CTkButton(bar, text="Export CSV", command=self._export_csv).pack(side="right", padx=8)

    def _prev_month(self):
        from utils.date_helpers import prev_month
        self._month_var.set(prev_month(self._month_var.get()))
        self._load()

    def _next_month(self):
        from utils.date_helpers import next_month
        self._month_var.set(next_month(self._month_var.get()))
        self._load()

    def _build_summary(self):
        self._summary_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._summary_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=10)
        self._summary_frame.grid_columnconfigure((0, 1, 2), weight=1)

    def _build_charts(self):
        charts = ctk.CTkFrame(self, fg_color="transparent")
        charts.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 12))
        charts.grid_columnconfigure(0, weight=3)
        charts.grid_columnconfigure(1, weight=2)
        charts.grid_rowconfigure(0, weight=1)

        # Bar chart frame
        bar_outer = ctk.CTkFrame(charts, fg_color=("gray90", "gray20"), corner_radius=8)
        bar_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ctk.CTkLabel(
            bar_outer, text="Monthly Income vs Expenses",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(pady=(10, 0))
        self._bar_fig = Figure(figsize=(5, 3), dpi=80, tight_layout=True)
        self._bar_ax = self._bar_fig.add_subplot(111)
        self._bar_mpl = FigureCanvasTkAgg(self._bar_fig, master=bar_outer)
        self._bar_mpl.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=(4, 10))

        # Pie chart frame
        pie_outer = ctk.CTkFrame(charts, fg_color=("gray90", "gray20"), corner_radius=8)
        pie_outer.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(
            pie_outer, text="Expense Breakdown",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(pady=(10, 0))
        self._pie_fig = Figure(figsize=(3, 3), dpi=80, tight_layout=True)
        self._pie_ax = self._pie_fig.add_subplot(111)
        self._pie_mpl = FigureCanvasTkAgg(self._pie_fig, master=pie_outer)
        self._pie_mpl.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=(4, 10))
        self._legend_frame = ctk.CTkFrame(pie_outer, fg_color="transparent")
        self._legend_frame.pack(fill="x", padx=8, pady=(0, 8))

    def _style_ax(self, ax, fig):
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg = "#2b2b2b" if is_dark else "#e4e4e4"
        fg = "#aaaaaa" if is_dark else "#444444"
        fig.patch.set_facecolor(bg)
        ax.set_facecolor(bg)
        ax.tick_params(colors=fg, labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor(fg)

    def _load(self):
        acct_name = self._acct_var.get()
        account_id = None
        if acct_name != "All Accounts":
            acct = next((a for a in self._accounts if a.name == acct_name), None)
            if acct:
                account_id = acct.id

        month = self._month_var.get()

        # Summary cards
        for w in self._summary_frame.winfo_children():
            w.destroy()
        summary = self._report_svc.get_summary(month, account_id)
        for i, (label, value, color) in enumerate([
            ("Income", summary["income"], "#4CAF50"),
            ("Expenses", summary["expense"], "#F44336"),
            ("Net", summary["net"], "#2196F3" if summary["net"] >= 0 else "#FF9800"),
        ]):
            card = ctk.CTkFrame(
                self._summary_frame, fg_color=("gray90", "gray20"), corner_radius=10
            )
            card.grid(row=0, column=i, padx=6, sticky="ew")
            ctk.CTkLabel(card, text=label, text_color="gray60").pack(pady=(10, 0), padx=16)
            ctk.CTkLabel(
                card, text=format_currency(value),
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color=color,
            ).pack(pady=(4, 10), padx=16)

        # Bar chart
        self.after(50, lambda: self._draw_bar_chart(account_id))

        # Pie chart
        breakdown = self._report_svc.get_category_breakdown(month, account_id)

        self.after(50, lambda b=breakdown: self._draw_pie_chart(b))
        for w in self._legend_frame.winfo_children():
            w.destroy()
        for item in breakdown[:8]:
            row = ctk.CTkFrame(self._legend_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)
            tk.Label(row, bg=item["color_hex"], width=2).pack(side="left", padx=(0, 4))
            ctk.CTkLabel(
                row, text=f"{item['category']}: {format_currency(item['total'])}",
                anchor="w", font=ctk.CTkFont(size=11),
            ).pack(side="left")

    def _draw_bar_chart(self, account_id):
        ax = self._bar_ax
        ax.clear()
        self._style_ax(ax, self._bar_fig)

        data = self._report_svc.get_monthly_chart_data(account_id, months=6)
        if not data:
            ax.text(0.5, 0.5, "No data", ha="center", va="center",
                    transform=ax.transAxes, color="gray")
            self._bar_mpl.draw_idle()
            return

        labels = [d["month"][5:] for d in data]
        incomes  = [d.get("income",  0) for d in data]
        expenses = [d.get("expense", 0) for d in data]
        x = list(range(len(labels)))
        w = 0.35
        ax.bar([i - w / 2 for i in x], incomes,  w, color="#4CAF50")
        ax.bar([i + w / 2 for i in x], expenses, w, color="#F44336")
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.yaxis.set_major_formatter(
            lambda v, _: f"{v/1000:.0f}k" if abs(v) >= 1000 else f"{v:.0f}"
        )
        self._bar_mpl.draw_idle()

    def _draw_pie_chart(self, breakdown):
        ax = self._pie_ax
        ax.clear()
        self._style_ax(ax, self._pie_fig)

        total = sum(d["total"] for d in breakdown) if breakdown else 0
        if not breakdown or total == 0:
            ax.text(0.5, 0.5, "No expense data", ha="center", va="center",
                    transform=ax.transAxes, color="gray")
            self._pie_mpl.draw_idle()
            return

        ax.pie(
            [d["total"] for d in breakdown],
            colors=[d["color_hex"] for d in breakdown],
            startangle=90,
        )
        ax.set_aspect("equal")
        self._pie_mpl.draw_idle()

    def _export_csv(self):
        from tkinter import filedialog
        acct_name = self._acct_var.get()
        account_id = None
        if acct_name != "All Accounts":
            acct = next((a for a in self._accounts if a.name == acct_name), None)
            if acct:
                account_id = acct.id

        month = self._month_var.get()
        rows = self._report_svc.export_csv(account_id, month)

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"budget_{month}.csv",
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)
