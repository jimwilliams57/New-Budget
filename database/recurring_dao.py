from typing import Optional
from database.db_manager import DatabaseManager
from models.recurring_rule import RecurringRule


class RecurringDAO:
    def __init__(self, db: DatabaseManager):
        self._db = db

    def _row_to_model(self, row) -> RecurringRule:
        return RecurringRule(
            id=row["id"],
            name=row["name"],
            type=row["type"],
            amount=row["amount"],
            account_id=row["account_id"],
            category_id=row["category_id"],
            description=row["description"],
            frequency=row["frequency"],
            start_date=row["start_date"],
            is_active=bool(row["is_active"]),
            day_of_month=row["day_of_month"],
            day_of_week=row["day_of_week"],
            month_of_year=row["month_of_year"],
            end_date=row["end_date"],
            last_applied=row["last_applied"],
            account_name=row["account_name"] if "account_name" in row.keys() else "",
            category_name=row["category_name"] if "category_name" in row.keys() else "",
        )

    def _select(self) -> str:
        return """
            SELECT r.*,
                   a.name AS account_name,
                   c.name AS category_name
            FROM recurring_rules r
            JOIN accounts a ON r.account_id = a.id
            JOIN categories c ON r.category_id = c.id
        """

    def get_all(self) -> list[RecurringRule]:
        conn = self._db.get_connection()
        rows = conn.execute(
            self._select() + " ORDER BY r.name"
        ).fetchall()
        return [self._row_to_model(r) for r in rows]

    def get_active(self) -> list[RecurringRule]:
        conn = self._db.get_connection()
        rows = conn.execute(
            self._select() + " WHERE r.is_active = 1 ORDER BY r.name"
        ).fetchall()
        return [self._row_to_model(r) for r in rows]

    def get_by_id(self, rule_id: int) -> Optional[RecurringRule]:
        conn = self._db.get_connection()
        row = conn.execute(
            self._select() + " WHERE r.id = ?", (rule_id,)
        ).fetchone()
        return self._row_to_model(row) if row else None

    def create(
        self,
        name: str,
        type_: str,
        amount: float,
        account_id: int,
        category_id: int,
        description: str,
        frequency: str,
        start_date: str,
        day_of_month: int | None = None,
        day_of_week: int | None = None,
        month_of_year: int | None = None,
        end_date: str | None = None,
    ) -> RecurringRule:
        conn = self._db.get_connection()
        cursor = conn.execute(
            """INSERT INTO recurring_rules
               (name, type, amount, account_id, category_id, description,
                frequency, start_date, day_of_month, day_of_week,
                month_of_year, end_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                name, type_, amount, account_id, category_id, description,
                frequency, start_date, day_of_month, day_of_week,
                month_of_year, end_date,
            ),
        )
        conn.commit()
        return self.get_by_id(cursor.lastrowid)

    def update(
        self,
        rule_id: int,
        name: str,
        type_: str,
        amount: float,
        account_id: int,
        category_id: int,
        description: str,
        frequency: str,
        start_date: str,
        day_of_month: int | None = None,
        day_of_week: int | None = None,
        month_of_year: int | None = None,
        end_date: str | None = None,
        is_active: bool = True,
    ) -> RecurringRule:
        conn = self._db.get_connection()
        conn.execute(
            """UPDATE recurring_rules SET
               name=?, type=?, amount=?, account_id=?, category_id=?,
               description=?, frequency=?, start_date=?, day_of_month=?,
               day_of_week=?, month_of_year=?, end_date=?, is_active=?
               WHERE id=?""",
            (
                name, type_, amount, account_id, category_id, description,
                frequency, start_date, day_of_month, day_of_week,
                month_of_year, end_date, 1 if is_active else 0, rule_id,
            ),
        )
        conn.commit()
        return self.get_by_id(rule_id)

    def set_active(self, rule_id: int, is_active: bool):
        conn = self._db.get_connection()
        conn.execute(
            "UPDATE recurring_rules SET is_active = ? WHERE id = ?",
            (1 if is_active else 0, rule_id),
        )
        conn.commit()

    def update_last_applied(self, rule_id: int, date_str: str):
        conn = self._db.get_connection()
        conn.execute(
            "UPDATE recurring_rules SET last_applied = ? WHERE id = ?",
            (date_str, rule_id),
        )
        conn.commit()

    def delete(self, rule_id: int):
        conn = self._db.get_connection()
        conn.execute("DELETE FROM recurring_rules WHERE id = ?", (rule_id,))
        conn.commit()
