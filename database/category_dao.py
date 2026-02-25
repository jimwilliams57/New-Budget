from typing import Optional
from database.db_manager import DatabaseManager
from models.category import Category


class CategoryDAO:
    def __init__(self, db: DatabaseManager):
        self._db = db
        self._all_cache: list | None = None

    def _invalidate_cache(self):
        self._all_cache = None

    def _row_to_model(self, row) -> Category:
        return Category(
            id=row["id"],
            name=row["name"],
            type=row["type"],
            color_hex=row["color_hex"],
            is_system=bool(row["is_system"]),
        )

    def get_all(self) -> list[Category]:
        if self._all_cache is None:
            conn = self._db.get_connection()
            rows = conn.execute(
                "SELECT * FROM categories ORDER BY name"
            ).fetchall()
            self._all_cache = [self._row_to_model(r) for r in rows]
        return self._all_cache

    def get_by_id(self, category_id: int) -> Optional[Category]:
        conn = self._db.get_connection()
        row = conn.execute(
            "SELECT * FROM categories WHERE id = ?", (category_id,)
        ).fetchone()
        return self._row_to_model(row) if row else None

    def get_by_type(self, type_filter: str) -> list[Category]:
        """type_filter: 'income', 'expense', or 'both'."""
        conn = self._db.get_connection()
        rows = conn.execute(
            "SELECT * FROM categories WHERE type = ? OR type = 'both' ORDER BY name",
            (type_filter,),
        ).fetchall()
        return [self._row_to_model(r) for r in rows]

    def get_for_transaction_type(self, tx_type: str) -> list[Category]:
        """Get categories valid for income or expense transactions."""
        if tx_type == "income":
            rows = self._db.get_connection().execute(
                "SELECT * FROM categories WHERE type IN ('income','both') ORDER BY name"
            ).fetchall()
        elif tx_type == "expense":
            rows = self._db.get_connection().execute(
                "SELECT * FROM categories WHERE type IN ('expense','both') ORDER BY name"
            ).fetchall()
        else:
            rows = self._db.get_connection().execute(
                "SELECT * FROM categories ORDER BY name"
            ).fetchall()
        return [self._row_to_model(r) for r in rows]

    def create(self, name: str, type_: str, color_hex: str = "#888888") -> Category:
        conn = self._db.get_connection()
        cursor = conn.execute(
            "INSERT INTO categories(name, type, color_hex) VALUES (?, ?, ?)",
            (name, type_, color_hex),
        )
        conn.commit()
        self._invalidate_cache()
        return self.get_by_id(cursor.lastrowid)

    def update(self, category_id: int, name: str, type_: str, color_hex: str) -> Category:
        conn = self._db.get_connection()
        conn.execute(
            "UPDATE categories SET name=?, type=?, color_hex=? WHERE id=?",
            (name, type_, color_hex, category_id),
        )
        conn.commit()
        self._invalidate_cache()
        return self.get_by_id(category_id)

    def delete(self, category_id: int):
        conn = self._db.get_connection()
        conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()
        self._invalidate_cache()
