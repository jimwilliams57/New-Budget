from typing import Optional
from database.db_manager import DatabaseManager
from models.account import Account


class AccountDAO:
    def __init__(self, db: DatabaseManager):
        self._db = db
        self._all_cache: list | None = None

    def _invalidate_cache(self):
        self._all_cache = None

    def _row_to_model(self, row) -> Account:
        return Account(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            account_type=row["account_type"],
            opening_balance=row["opening_balance"],
            created_at=row["created_at"],
        )

    def get_all(self) -> list[Account]:
        if self._all_cache is None:
            conn = self._db.get_connection()
            rows = conn.execute(
                "SELECT * FROM accounts ORDER BY name"
            ).fetchall()
            self._all_cache = [self._row_to_model(r) for r in rows]
        return self._all_cache

    def get_by_id(self, account_id: int) -> Optional[Account]:
        conn = self._db.get_connection()
        row = conn.execute(
            "SELECT * FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()
        return self._row_to_model(row) if row else None

    def get_by_name(self, name: str) -> Optional[Account]:
        conn = self._db.get_connection()
        row = conn.execute(
            "SELECT * FROM accounts WHERE name = ?", (name,)
        ).fetchone()
        return self._row_to_model(row) if row else None

    def create(
        self,
        name: str,
        description: str = "",
        account_type: str = "checking",
        opening_balance: float = 0.0,
    ) -> Account:
        conn = self._db.get_connection()
        cursor = conn.execute(
            "INSERT INTO accounts(name, description, account_type, opening_balance) VALUES (?, ?, ?, ?)",
            (name, description, account_type, opening_balance),
        )
        conn.commit()
        self._invalidate_cache()
        return self.get_by_id(cursor.lastrowid)

    def update(
        self,
        account_id: int,
        name: str,
        description: str = "",
        account_type: str = "checking",
        opening_balance: float = 0.0,
    ) -> Account:
        conn = self._db.get_connection()
        conn.execute(
            "UPDATE accounts SET name = ?, description = ?, account_type = ?, opening_balance = ? WHERE id = ?",
            (name, description, account_type, opening_balance, account_id),
        )
        conn.commit()
        self._invalidate_cache()
        return self.get_by_id(account_id)

    def delete(self, account_id: int):
        conn = self._db.get_connection()
        conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        conn.commit()
        self._invalidate_cache()

    def has_transactions(self, account_id: int) -> bool:
        conn = self._db.get_connection()
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM transactions WHERE account_id = ?",
            (account_id,),
        ).fetchone()
        return row["cnt"] > 0
