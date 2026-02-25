import threading
import customtkinter as ctk
import tkinter as tk

from services.net_worth_service import NetWorthService
from utils.currency import format_currency


class NetWorthTab(ctk.CTkFrame):
    def __init__(self, master, net_worth_service: NetWorthService, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._svc = net_worth_service
        self._months_var = ctk.IntVar(value=12)
        self._load_gen = 0

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._build_headline()
        self._build_breakdown()
        self._build_toolbar()
        self._build_chart()

        self.after(100, self._load)

    def refresh(self):
        self._load()

    # ── Layout builders ───────────────────────────────────────────────────────

    def _build_headline(self):
        card = ctk.CTkFrame(self, fg_color=("gray88", "gray18"), corner_radius=8)
        card.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))
        card.grid_columnconfigure(0, weight=1)

        self._headline_amount = ctk.CTkLabel(
            card, text="",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        self._headline_amount.pack(pady=(12, 2))

        self._headline_subtitle = ctk.CTkLabel(
            card, text="",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
        )
        self._headline_subtitle.pack(pady=(0, 10))

    def _build_breakdown(self):
        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.grid(row=1, column=0, sticky="ew", padx=8, pady=(8, 0))
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_columnconfigure(1, weight=1)

        # Assets panel
        assets_panel = ctk.CTkScrollableFrame(
            outer, label_text="ASSETS", height=150,
        )
        assets_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        assets_panel.grid_columnconfigure(0, weight=1)
        assets_panel.grid_columnconfigure(1, weight=0)
        self._assets_frame = assets_panel

        # Liabilities panel
        liab_panel = ctk.CTkScrollableFrame(
            outer, label_text="LIABILITIES", height=150,
        )
        liab_panel.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        liab_panel.grid_columnconfigure(0, weight=1)
        liab_panel.grid_columnconfigure(1, weight=0)
        self._liab_frame = liab_panel

    def _build_toolbar(self):
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=2, column=0, sticky="ew", padx=8, pady=(8, 0))

        ctk.CTkLabel(bar, text="History:").pack(side="left", padx=(0, 8))
        ctk.CTkSegmentedButton(
            bar,
            values=["12 months", "24 months"],
            command=self._on_months_changed,
        ).pack(side="left")
        # Store reference to set default after build
        self._months_seg = bar.winfo_children()[-1]

    def _build_chart(self):
        outer = ctk.CTkFrame(self, fg_color=("gray90", "gray20"), corner_radius=8)
        outer.grid(row=3, column=0, sticky="nsew", padx=8, pady=8)
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(0, weight=1)

        self._chart_canvas = tk.Canvas(
            outer, height=200, highlightthickness=0,
            bg=self._canvas_bg(),
        )
        self._chart_canvas.grid(row=0, column=0, sticky="ew", padx=8, pady=8)

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _on_months_changed(self, value: str):
        self._months_var.set(12 if value == "12 months" else 24)
        self._load()

    def _canvas_bg(self) -> str:
        return "#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#e8e8e8"

    # ── Data loading ──────────────────────────────────────────────────────────

    def _load(self):
        self._load_gen += 1
        gen = self._load_gen
        months = self._months_var.get()

        def fetch():
            try:
                breakdown = self._svc.get_current_breakdown()
                history = self._svc.get_monthly_history(months=months)
            except Exception:
                breakdown = None
                history = []
            self.after(0, lambda: self._on_data_ready(gen, breakdown, history))

        threading.Thread(target=fetch, daemon=True).start()

    def _on_data_ready(self, gen: int, breakdown: dict | None, history: list[dict]):
        if gen != self._load_gen:
            return
        if not self.winfo_exists():
            return
        if breakdown is None:
            return

        # Update headline
        net_worth = breakdown["net_worth"]
        color = "#4CAF50" if net_worth >= 0 else "#F44336"
        self._headline_amount.configure(
            text=format_currency(net_worth),
            text_color=color,
        )
        self._headline_subtitle.configure(text=f"as of {breakdown['as_of_month']}")

        # Repopulate assets
        self._populate_panel(
            self._assets_frame,
            rows=[(a["name"], a["balance"]) for a in breakdown["assets"]],
            total=breakdown["total_assets"],
            value_color="#4CAF50",
        )

        # Repopulate liabilities
        self._populate_panel(
            self._liab_frame,
            rows=[(l["name"], l["amount_owed"]) for l in breakdown["liabilities"]],
            total=breakdown["total_liabilities"],
            value_color="#F44336",
        )

        self._chart_canvas.configure(bg=self._canvas_bg())
        self._chart_canvas.after(50, lambda h=history: self._draw_bar_chart(h))

    def _populate_panel(self, frame, rows: list[tuple], total: float, value_color: str):
        for w in frame.winfo_children():
            w.destroy()

        for i, (name, value) in enumerate(rows):
            ctk.CTkLabel(
                frame, text=name, anchor="w",
            ).grid(row=i, column=0, sticky="w", padx=(4, 8), pady=2)
            ctk.CTkLabel(
                frame, text=format_currency(value),
                text_color=value_color, anchor="e",
            ).grid(row=i, column=1, sticky="e", padx=4, pady=2)

        # Separator
        sep_row = len(rows)
        sep = ctk.CTkFrame(frame, height=1, fg_color=("gray70", "gray40"))
        sep.grid(row=sep_row, column=0, columnspan=2, sticky="ew", padx=4, pady=(4, 2))

        # Total row
        ctk.CTkLabel(
            frame, text="Total",
            font=ctk.CTkFont(weight="bold"), anchor="w",
        ).grid(row=sep_row + 1, column=0, sticky="w", padx=(4, 8), pady=2)
        ctk.CTkLabel(
            frame, text=format_currency(total),
            text_color=value_color,
            font=ctk.CTkFont(weight="bold"), anchor="e",
        ).grid(row=sep_row + 1, column=1, sticky="e", padx=4, pady=2)

    # ── Chart drawing ─────────────────────────────────────────────────────────

    def _draw_bar_chart(self, history: list[dict]):
        canvas = self._chart_canvas
        canvas.delete("all")

        if not history:
            canvas.create_text(200, 100, text="No data", fill="gray")
            return

        values = [h["net_worth"] for h in history]
        max_val = max(values) if values else 0.0
        min_val = min(values) if values else 0.0

        # Ensure range is non-zero
        if max_val == min_val:
            max_val = max_val + 1 if max_val >= 0 else 0.0
            min_val = min_val - 1 if min_val <= 0 else 0.0
        if max_val < 0:
            max_val = 0.0
        if min_val > 0:
            min_val = 0.0

        n = len(history)
        padding_left = 60
        padding_right = 12
        padding_top = 16
        padding_bottom = 32
        h = 200

        canvas_w = canvas.winfo_width()
        if canvas_w < 50:
            canvas_w = 600

        chart_w = canvas_w - padding_left - padding_right
        bar_w = max(4, (chart_w / n) * 0.6)
        total_range = max_val - min_val

        def y_for_val(val: float) -> float:
            bar_area_h = h - padding_top - padding_bottom
            frac = (val - min_val) / total_range
            return h - padding_bottom - frac * bar_area_h

        zero_y = y_for_val(0.0)
        bar_area_h = h - padding_top - padding_bottom

        # Grid lines and Y-axis labels
        for frac, val in [
            (1.0, max_val),
            (0.5, (max_val + min_val) / 2),
            (0.0, min_val),
        ]:
            gy = padding_top + (1.0 - frac) * bar_area_h
            text_color = "#888888"
            canvas.create_line(
                padding_left - 4, gy, canvas_w - padding_right, gy,
                fill=text_color, dash=(2, 4),
            )
            canvas.create_text(
                padding_left - 6, gy,
                text=_short_amount(val),
                anchor="e", fill=text_color, font=("Arial", 7),
            )

        # Zero baseline (solid)
        canvas.create_line(
            padding_left, zero_y, canvas_w - padding_right, zero_y,
            fill="#888888", width=1,
        )

        for i, entry in enumerate(history):
            nw = entry["net_worth"]
            x_center = padding_left + (i + 0.5) * (chart_w / n)
            bar_color = "#4CAF50" if nw >= 0 else "#F44336"
            bar_y = y_for_val(nw)

            canvas.create_rectangle(
                x_center - bar_w / 2, min(bar_y, zero_y),
                x_center + bar_w / 2, max(bar_y, zero_y),
                fill=bar_color, outline="",
            )

            # X-axis label (month portion)
            label = entry["month"][5:]  # "MM"
            canvas.create_text(
                x_center, h - padding_bottom + 12,
                text=label, fill="gray", font=("Arial", 8),
            )


def _short_amount(value: float) -> str:
    """Format a number compactly for chart axis labels, handling negatives."""
    sign = "-" if value < 0 else ""
    abs_val = abs(value)
    if abs_val >= 1_000_000:
        return f"{sign}{abs_val / 1_000_000:.1f}M"
    if abs_val >= 1_000:
        return f"{sign}{abs_val / 1_000:.0f}k"
    return f"{sign}{abs_val:.0f}"
