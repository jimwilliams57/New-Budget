from database.db_manager import DatabaseManager


class DismissedReminderDAO:
    """Persists per-reminder dismissals with expiry dates."""

    def __init__(self, db: DatabaseManager):
        self._db = db

    def dismiss(self, key: str, expires: str) -> None:
        """Insert or replace a dismissal record. expires is YYYY-MM-DD."""
        conn = self._db.get_connection()
        conn.execute(
            "INSERT OR REPLACE INTO dismissed_reminders(key, expires) VALUES (?, ?)",
            (key, expires),
        )
        conn.commit()

    def get_active_keys(self, ref_date: str) -> set[str]:
        """Purge expired rows, then return the set of non-expired dismissed keys."""
        conn = self._db.get_connection()
        conn.execute(
            "DELETE FROM dismissed_reminders WHERE expires < ?", (ref_date,)
        )
        conn.commit()
        rows = conn.execute(
            "SELECT key FROM dismissed_reminders WHERE expires >= ?", (ref_date,)
        ).fetchall()
        return {row["key"] for row in rows}

    def undismiss(self, key: str) -> None:
        """Remove a specific dismissal record."""
        conn = self._db.get_connection()
        conn.execute("DELETE FROM dismissed_reminders WHERE key = ?", (key,))
        conn.commit()
