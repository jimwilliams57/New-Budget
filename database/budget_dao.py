from typing import Optional
from database.db_manager import DatabaseManager
from models.budget import Budget


class BudgetDAO:
    def __init__(self, db: DatabaseManager):
        self._db = db

    def _row_to_model(self, row, spent: float = 0.0) -> Budget:
        return Budget(
            id=row["id"],
            category_id=row["category_id"],
            category_name=row["category_name"] if "category_name" in row.keys() else "",
            month=row["month"],
            limit_amount=row["limit_amount"],
            spent_amount=spent,
            color_hex=row["color_hex"] if "color_hex" in row.keys() else "#888888",
        )

    def get_all(self) -> list[Budget]:
        conn = self._db.get_connection()
        rows = conn.execute(
            """SELECT b.*, c.name AS category_name, c.color_hex
               FROM budgets b JOIN categories c ON b.category_id = c.id
               ORDER BY b.month, c.name"""
        ).fetchall()
        return [self._row_to_model(r) for r in rows]

    def get_by_month(self, month: str) -> list[Budget]:
        conn = self._db.get_connection()
        rows = conn.execute(
            """SELECT b.*, c.name AS category_name, c.color_hex
               FROM budgets b
               JOIN categories c ON b.category_id = c.id
               WHERE b.month = ?
               ORDER BY c.name""",
            (month,),
        ).fetchall()
        return [self._row_to_model(r) for r in rows]

    def get_by_category_month(self, category_id: int, month: str) -> Optional[Budget]:
        conn = self._db.get_connection()
        row = conn.execute(
            """SELECT b.*, c.name AS category_name, c.color_hex
               FROM budgets b
               JOIN categories c ON b.category_id = c.id
               WHERE b.category_id = ? AND b.month = ?""",
            (category_id, month),
        ).fetchone()
        return self._row_to_model(row) if row else None

    def upsert(self, category_id: int, month: str, limit_amount: float) -> Budget:
        conn = self._db.get_connection()
        conn.execute(
            """INSERT INTO budgets(category_id, month, limit_amount)
               VALUES (?, ?, ?)
               ON CONFLICT(category_id, month)
               DO UPDATE SET limit_amount = excluded.limit_amount""",
            (category_id, month, limit_amount),
        )
        conn.commit()
        return self.get_by_category_month(category_id, month)

    def delete(self, budget_id: int):
        conn = self._db.get_connection()
        conn.execute("DELETE FROM budgets WHERE id = ?", (budget_id,))
        conn.commit()

    def copy_month(self, from_month: str, to_month: str) -> int:
        """Copy all budget limits from one month to another. Returns count copied."""
        conn = self._db.get_connection()
        rows = conn.execute(
            "SELECT category_id, limit_amount FROM budgets WHERE month = ?",
            (from_month,),
        ).fetchall()
        count = 0
        for row in rows:
            conn.execute(
                """INSERT INTO budgets(category_id, month, limit_amount)
                   VALUES (?, ?, ?)
                   ON CONFLICT(category_id, month)
                   DO UPDATE SET limit_amount = excluded.limit_amount""",
                (row["category_id"], to_month, row["limit_amount"]),
            )
            count += 1
        conn.commit()
        return count
