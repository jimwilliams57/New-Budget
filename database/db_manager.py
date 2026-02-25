import sqlite3
import os
from datetime import date
from utils.constants import DB_FILE, DEFAULT_CATEGORIES, DEFAULT_ACCOUNT_NAME, db_file_for_year


class DatabaseManager:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or DB_FILE
        self._conn: sqlite3.Connection | None = None

    def get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA journal_mode = WAL")
        return self._conn

    def initialize(self):
        """Create schema and seed defaults."""
        conn = self.get_connection()
        self._create_schema(conn)
        self._migrate_schema(conn)
        self._seed_defaults(conn)
        conn.commit()

    def _migrate_schema(self, conn: sqlite3.Connection):
        """Idempotent ALTER TABLE for columns added after initial release."""
        cols = {row[1] for row in conn.execute("PRAGMA table_info(accounts)").fetchall()}
        if "account_type" not in cols:
            conn.execute(
                "ALTER TABLE accounts ADD COLUMN account_type TEXT NOT NULL DEFAULT 'checking'"
            )
        if "opening_balance" not in cols:
            conn.execute(
                "ALTER TABLE accounts ADD COLUMN opening_balance REAL NOT NULL DEFAULT 0.0"
            )

    def _create_schema(self, conn: sqlite3.Connection):
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS accounts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT    NOT NULL UNIQUE,
                description     TEXT    NOT NULL DEFAULT '',
                account_type    TEXT    NOT NULL DEFAULT 'checking',
                opening_balance REAL    NOT NULL DEFAULT 0.0,
                created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS categories (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL UNIQUE,
                type       TEXT NOT NULL CHECK(type IN ('income','expense','both')),
                color_hex  TEXT NOT NULL DEFAULT '#888888',
                is_system  INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS recurring_rules (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                type          TEXT NOT NULL CHECK(type IN ('income','expense')),
                amount        REAL NOT NULL CHECK(amount > 0),
                account_id    INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                category_id   INTEGER NOT NULL REFERENCES categories(id),
                description   TEXT NOT NULL DEFAULT '',
                frequency     TEXT NOT NULL CHECK(frequency IN ('monthly','weekly','yearly')),
                day_of_month  INTEGER,
                day_of_week   INTEGER,
                month_of_year INTEGER,
                start_date    TEXT NOT NULL,
                end_date      TEXT,
                is_active     INTEGER NOT NULL DEFAULT 1,
                last_applied  TEXT
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id        INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                type              TEXT NOT NULL CHECK(type IN ('income','expense','transfer')),
                amount            REAL NOT NULL CHECK(amount > 0),
                category_id       INTEGER REFERENCES categories(id) ON DELETE RESTRICT,
                description       TEXT NOT NULL DEFAULT '',
                date              TEXT NOT NULL,
                cleared           INTEGER NOT NULL DEFAULT 0,
                transfer_pair_id  INTEGER,
                recurring_rule_id INTEGER REFERENCES recurring_rules(id) ON DELETE SET NULL,
                created_at        TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at        TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_transactions_account_id   ON transactions(account_id);
            CREATE INDEX IF NOT EXISTS idx_transactions_date         ON transactions(date);
            CREATE INDEX IF NOT EXISTS idx_transactions_category_id  ON transactions(category_id);
            CREATE INDEX IF NOT EXISTS idx_transactions_transfer_pair ON transactions(transfer_pair_id);
            CREATE INDEX IF NOT EXISTS idx_budgets_month             ON budgets(month);

            CREATE TABLE IF NOT EXISTS budgets (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id  INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                month        TEXT NOT NULL,
                limit_amount REAL NOT NULL CHECK(limit_amount >= 0),
                UNIQUE(category_id, month)
            );

            CREATE TABLE IF NOT EXISTS app_settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS dismissed_reminders (
                key     TEXT PRIMARY KEY,
                expires TEXT NOT NULL
            );
        """)

    def _seed_defaults(self, conn: sqlite3.Connection):
        # Default settings
        defaults = [
            ("appearance_mode", "system"),
            ("currency_symbol", "$"),
            ("budget_alert_threshold", "0.80"),
            ("last_account_id", ""),
            ("date_format", "MM/DD/YYYY"),
        ]
        for key, value in defaults:
            conn.execute(
                "INSERT OR IGNORE INTO app_settings(key, value) VALUES (?, ?)",
                (key, value),
            )

        # Default categories
        for cat in DEFAULT_CATEGORIES:
            conn.execute(
                """INSERT OR IGNORE INTO categories(name, type, color_hex, is_system)
                   VALUES (?, ?, ?, ?)""",
                (cat["name"], cat["type"], cat["color_hex"], cat["is_system"]),
            )

        # Default account
        conn.execute(
            "INSERT OR IGNORE INTO accounts(name, description) VALUES (?, ?)",
            (DEFAULT_ACCOUNT_NAME, "Primary checking account"),
        )

    def get_setting(self, key: str, default: str = "") -> str:
        conn = self.get_connection()
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        conn = self.get_connection()
        conn.execute(
            "INSERT OR REPLACE INTO app_settings(key, value) VALUES (?, ?)",
            (key, value),
        )
        conn.commit()

    @staticmethod
    def open_for_current_year(db_folder: str | None = None) -> "DatabaseManager":
        """Startup factory: opens the correct year-keyed DB, migrating budget.db if needed.

        db_folder: if provided, DB files are stored in that directory instead of CWD.
        """
        current_year = date.today().year

        if db_folder:
            current_db_path = os.path.join(db_folder, f"budget_{current_year}.db")
            prev_db_path = os.path.join(db_folder, f"budget_{current_year - 1}.db")
            legacy_path = os.path.join(db_folder, "budget.db")
        else:
            current_db_path = db_file_for_year(current_year)
            prev_db_path = db_file_for_year(current_year - 1)
            legacy_path = DB_FILE

        # One-time migration: rename legacy budget.db → budget_YYYY.db
        if os.path.exists(legacy_path) and not os.path.exists(current_db_path):
            legacy_year = DatabaseManager._detect_legacy_year(legacy_path, current_year)
            if db_folder:
                legacy_dest = os.path.join(db_folder, f"budget_{legacy_year}.db")
            else:
                legacy_dest = db_file_for_year(legacy_year)
            if not os.path.exists(legacy_dest):
                os.rename(legacy_path, legacy_dest)
            if legacy_year == current_year - 1:
                prev_db_path = legacy_dest

        # Open / create current year DB
        db = DatabaseManager(current_db_path)
        db.initialize()

        # Budget carryover from previous year when this DB is new or incomplete
        if os.path.exists(prev_db_path):
            month_count = db.get_connection().execute(
                "SELECT COUNT(DISTINCT month) FROM budgets"
            ).fetchone()[0]
            if month_count < 12:
                DatabaseManager._carry_over_budgets(prev_db_path, db, current_year)

        return db

    @staticmethod
    def _detect_legacy_year(legacy_path: str, current_year: int) -> int:
        """Read MAX(date) from the legacy DB to determine which year it belongs to."""
        try:
            conn = sqlite3.connect(legacy_path)
            row = conn.execute("SELECT MAX(date) FROM transactions").fetchone()
            conn.close()
            if row and row[0]:
                return int(row[0][:4])
        except Exception:
            pass
        return current_year - 1

    @staticmethod
    def _carry_over_budgets(prev_db_path: str, current_db: "DatabaseManager", current_year: int):
        """Copy budget limits from the previous year into all 12 months of current_year."""
        try:
            prev_conn = sqlite3.connect(prev_db_path)
            prev_conn.row_factory = sqlite3.Row
            prev_year = current_year - 1

            # Priority: December of prev year → most recent month → skip
            source_month = f"{prev_year}-12"
            rows = prev_conn.execute(
                "SELECT category_id, limit_amount FROM budgets WHERE month = ?",
                (source_month,),
            ).fetchall()

            if not rows:
                fallback = prev_conn.execute(
                    "SELECT month FROM budgets ORDER BY month DESC LIMIT 1"
                ).fetchone()
                if fallback:
                    source_month = fallback["month"]
                    rows = prev_conn.execute(
                        "SELECT category_id, limit_amount FROM budgets WHERE month = ?",
                        (source_month,),
                    ).fetchall()

            prev_conn.close()

            if not rows:
                return

            conn = current_db.get_connection()
            for month_num in range(1, 13):
                month_str = f"{current_year}-{month_num:02d}"
                for row in rows:
                    conn.execute(
                        """INSERT INTO budgets(category_id, month, limit_amount)
                           VALUES (?, ?, ?)
                           ON CONFLICT(category_id, month)
                           DO UPDATE SET limit_amount = excluded.limit_amount""",
                        (row["category_id"], month_str, row["limit_amount"]),
                    )
            conn.commit()
        except Exception:
            pass  # Carryover is best-effort; never crash startup

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
