from typing import Optional
from database.db_manager import DatabaseManager
from models.transaction import Transaction


class TransactionDAO:
    def __init__(self, db: DatabaseManager):
        self._db = db

    def _row_to_model(self, row) -> Transaction:
        return Transaction(
            id=row["id"],
            account_id=row["account_id"],
            type=row["type"],
            amount=row["amount"],
            category_id=row["category_id"],
            category_name=row["category_name"] if "category_name" in row.keys() else "",
            description=row["description"],
            date=row["date"],
            cleared=bool(row["cleared"]),
            transfer_pair_id=row["transfer_pair_id"],
            recurring_rule_id=row["recurring_rule_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _select(self) -> str:
        return """
            SELECT t.*,
                   COALESCE(c.name, '') AS category_name
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
        """

    def get_all(self) -> list[Transaction]:
        conn = self._db.get_connection()
        rows = conn.execute(
            self._select() + " ORDER BY t.date ASC, t.id ASC"
        ).fetchall()
        return [self._row_to_model(r) for r in rows]

    def get_by_account(
        self,
        account_id: int,
        month: str | None = None,
        type_filter: str | None = None,
        cleared_filter: str | None = None,
        search: str | None = None,
    ) -> list[Transaction]:
        conn = self._db.get_connection()
        sql = self._select() + " WHERE t.account_id = ?"
        params: list = [account_id]

        if month:
            sql += " AND strftime('%Y-%m', t.date) = ?"
            params.append(month)
        if type_filter and type_filter != "all":
            sql += " AND t.type = ?"
            params.append(type_filter)
        if cleared_filter == "cleared":
            sql += " AND t.cleared = 1"
        elif cleared_filter == "pending":
            sql += " AND t.cleared = 0"
        if search:
            sql += " AND (t.description LIKE ? OR COALESCE(c.name,'') LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        sql += " ORDER BY t.date ASC, t.id ASC"
        rows = conn.execute(sql, params).fetchall()
        return [self._row_to_model(r) for r in rows]

    def get_by_id(self, tx_id: int) -> Optional[Transaction]:
        conn = self._db.get_connection()
        row = conn.execute(
            self._select() + " WHERE t.id = ?", (tx_id,)
        ).fetchone()
        return self._row_to_model(row) if row else None

    def get_by_transfer_pair(self, pair_id: int) -> list[Transaction]:
        conn = self._db.get_connection()
        rows = conn.execute(
            self._select() + " WHERE t.transfer_pair_id = ?", (pair_id,)
        ).fetchall()
        return [self._row_to_model(r) for r in rows]

    def get_by_transfer_pair_ids(self, pair_ids: list[int]) -> dict[int, list["Transaction"]]:
        """Fetch all rows for multiple transfer_pair_ids in a single query.
        Returns {pair_id: [tx, ...]}."""
        if not pair_ids:
            return {}
        conn = self._db.get_connection()
        placeholders = ",".join("?" * len(pair_ids))
        rows = conn.execute(
            self._select() + f" WHERE t.transfer_pair_id IN ({placeholders})", pair_ids
        ).fetchall()
        result: dict[int, list[Transaction]] = {}
        for row in rows:
            tx = self._row_to_model(row)
            result.setdefault(tx.transfer_pair_id, []).append(tx)
        return result

    def get_by_category_and_month(self, category_id: int, month: str) -> list[Transaction]:
        conn = self._db.get_connection()
        rows = conn.execute(
            self._select() + """
            WHERE t.category_id = ?
              AND strftime('%Y-%m', t.date) = ?
              AND t.type = 'expense'
            """,
            (category_id, month),
        ).fetchall()
        return [self._row_to_model(r) for r in rows]

    def get_spending_by_category(self, month: str) -> dict[int, float]:
        """Sum of expense amounts per category_id for the given month (all accounts)."""
        conn = self._db.get_connection()
        rows = conn.execute(
            """SELECT category_id, SUM(amount) as total
               FROM transactions
               WHERE type = 'expense'
                 AND strftime('%Y-%m', date) = ?
                 AND category_id IS NOT NULL
               GROUP BY category_id""",
            (month,),
        ).fetchall()
        return {r["category_id"]: r["total"] for r in rows}

    def get_totals_for_month(self, month: str) -> dict:
        """Return income and expense totals across all accounts for the given month."""
        conn = self._db.get_connection()
        row = conn.execute(
            """SELECT
                SUM(CASE WHEN type='income'  THEN amount ELSE 0 END) AS income,
                SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) AS expense
               FROM transactions
               WHERE strftime('%Y-%m', date) = ?""",
            (month,),
        ).fetchone()
        return {
            "income":  row["income"]  or 0.0,
            "expense": row["expense"] or 0.0,
        }

    def get_totals_by_account(self, account_id: int, month: str) -> dict:
        """Return income, expense totals for one account/month."""
        conn = self._db.get_connection()
        row = conn.execute(
            """SELECT
                SUM(CASE WHEN type='income' THEN amount ELSE 0 END) AS income,
                SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) AS expense
               FROM transactions
               WHERE account_id = ?
                 AND strftime('%Y-%m', date) = ?""",
            (account_id, month),
        ).fetchone()
        return {
            "income": row["income"] or 0.0,
            "expense": row["expense"] or 0.0,
        }

    def create(
        self,
        account_id: int,
        type_: str,
        amount: float,
        date: str,
        description: str = "",
        category_id: int | None = None,
        cleared: bool = False,
        transfer_pair_id: int | None = None,
        recurring_rule_id: int | None = None,
    ) -> Transaction:
        conn = self._db.get_connection()
        cursor = conn.execute(
            """INSERT INTO transactions
               (account_id, type, amount, category_id, description, date,
                cleared, transfer_pair_id, recurring_rule_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                account_id, type_, amount, category_id, description, date,
                1 if cleared else 0, transfer_pair_id, recurring_rule_id,
            ),
        )
        return self.get_by_id(cursor.lastrowid)

    def update(
        self,
        tx_id: int,
        type_: str,
        amount: float,
        date: str,
        description: str = "",
        category_id: int | None = None,
        cleared: bool = False,
    ) -> Transaction:
        conn = self._db.get_connection()
        conn.execute(
            """UPDATE transactions
               SET type=?, amount=?, category_id=?, description=?, date=?,
                   cleared=?, updated_at=datetime('now')
               WHERE id=?""",
            (type_, amount, category_id, description, date,
             1 if cleared else 0, tx_id),
        )
        conn.commit()
        return self.get_by_id(tx_id)

    def set_cleared(self, tx_id: int, cleared: bool):
        conn = self._db.get_connection()
        conn.execute(
            "UPDATE transactions SET cleared=?, updated_at=datetime('now') WHERE id=?",
            (1 if cleared else 0, tx_id),
        )
        conn.commit()

    def delete(self, tx_id: int):
        conn = self._db.get_connection()
        conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
        conn.commit()

    def delete_by_transfer_pair(self, pair_id: int):
        conn = self._db.get_connection()
        conn.execute(
            "DELETE FROM transactions WHERE transfer_pair_id = ?", (pair_id,)
        )
        conn.commit()

    def get_balances_as_of(self, as_of_date: str | None = None) -> dict[int, float]:
        """Return {account_id: balance} for all accounts using a single aggregate query.
        If as_of_date (YYYY-MM-DD) is given, only transactions on or before that date
        are included.  Respects the debit/credit transfer convention (lower id = debit)."""
        conn = self._db.get_connection()
        date_clause = "AND t.date <= ?" if as_of_date else ""
        params = (as_of_date,) if as_of_date else ()
        rows = conn.execute(f"""
            WITH transfer_debit AS (
                SELECT MIN(id) AS debit_id, transfer_pair_id
                FROM transactions
                WHERE type = 'transfer'
                GROUP BY transfer_pair_id
            )
            SELECT
                t.account_id,
                SUM(
                    CASE t.type
                        WHEN 'income'   THEN  t.amount
                        WHEN 'expense'  THEN -t.amount
                        WHEN 'transfer' THEN
                            CASE WHEN t.id = td.debit_id THEN -t.amount ELSE t.amount END
                        ELSE 0
                    END
                ) AS balance
            FROM transactions t
            LEFT JOIN transfer_debit td ON t.transfer_pair_id = td.transfer_pair_id
            WHERE 1=1 {date_clause}
            GROUP BY t.account_id
        """, params).fetchall()
        return {r["account_id"]: r["balance"] for r in rows}

    def get_next_transfer_pair_id(self) -> int:
        conn = self._db.get_connection()
        row = conn.execute(
            "SELECT COALESCE(MAX(transfer_pair_id), 0) + 1 AS next_id FROM transactions"
        ).fetchone()
        return row["next_id"]

    def get_monthly_totals(
        self, account_id: int | None, months: int = 6
    ) -> list[dict]:
        """Return list of {month, income, expense} for the last N months."""
        conn = self._db.get_connection()
        where = "WHERE account_id = ?" if account_id else "WHERE 1=1"
        params = [account_id] if account_id else []
        rows = conn.execute(
            f"""SELECT strftime('%Y-%m', date) AS month,
                       SUM(CASE WHEN type='income' THEN amount ELSE 0 END) AS income,
                       SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) AS expense
                FROM transactions
                {where}
                GROUP BY month
                ORDER BY month DESC
                LIMIT ?""",
            params + [months],
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def get_avg_monthly_nonrecurring(self, account_id, months: int = 6) -> dict:
        """Average monthly income/expense from non-recurring transactions over last N months."""
        conn = self._db.get_connection()
        where_acct = "AND account_id = ?" if account_id else ""
        params = [account_id] if account_id else []
        rows = conn.execute(
            f"""SELECT strftime('%Y-%m', date) AS month,
                       SUM(CASE WHEN type='income' THEN amount ELSE 0 END) AS income,
                       SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) AS expense
                FROM transactions
                WHERE recurring_rule_id IS NULL
                  {where_acct}
                GROUP BY month
                ORDER BY month DESC
                LIMIT ?""",
            params + [months],
        ).fetchall()
        count = len(rows)
        if count == 0:
            return {"income": 0.0, "expense": 0.0}
        return {
            "income": sum(r["income"] for r in rows) / count,
            "expense": sum(r["expense"] for r in rows) / count,
        }

    def get_expense_by_category(self, month: str, account_id: int | None = None) -> list[dict]:
        conn = self._db.get_connection()
        where = "AND t.account_id = ?" if account_id else ""
        params = [month]
        if account_id:
            params.append(account_id)
        rows = conn.execute(
            f"""SELECT COALESCE(c.name,'Uncategorized') AS category,
                       COALESCE(c.color_hex,'#888888') AS color_hex,
                       SUM(t.amount) AS total
                FROM transactions t
                LEFT JOIN categories c ON t.category_id = c.id
                WHERE t.type = 'expense'
                  AND strftime('%Y-%m', t.date) = ?
                  {where}
                GROUP BY t.category_id
                ORDER BY total DESC""",
            params,
        ).fetchall()
        return [dict(r) for r in rows]
