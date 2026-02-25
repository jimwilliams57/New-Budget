"""Export and import all user data (accounts, categories, budgets,
recurring rules, transactions) as JSON or CSV-in-ZIP.
"""
import csv
import io
import json
import zipfile
from datetime import datetime

from database.db_manager import DatabaseManager
from database.account_dao import AccountDAO
from database.category_dao import CategoryDAO
from database.budget_dao import BudgetDAO
from database.recurring_dao import RecurringDAO
from database.transaction_dao import TransactionDAO
from services.transaction_service import TransactionService
from utils.date_helpers import today_str


class DataService:
    def __init__(
        self,
        db: DatabaseManager,
        account_dao: AccountDAO,
        category_dao: CategoryDAO,
        budget_dao: BudgetDAO,
        recurring_dao: RecurringDAO,
        tx_dao: TransactionDAO,
        tx_service: TransactionService,
    ):
        self._db = db
        self._account_dao = account_dao
        self._category_dao = category_dao
        self._budget_dao = budget_dao
        self._recurring_dao = recurring_dao
        self._tx_dao = tx_dao
        self._tx_svc = tx_service

    # ── Export ────────────────────────────────────────────────────────────────

    def export_json(self) -> dict:
        """Return a full export dict (caller writes to disk)."""
        return {
            "export_version": 1,
            "exported_at": datetime.now().isoformat(),
            "accounts": self._build_accounts(),
            "categories": self._build_categories(),
            "budgets": self._build_budgets(),
            "recurring_rules": self._build_recurring(),
            "transactions": self._build_transactions(),
        }

    def export_csv_zip(self, path: str) -> None:
        """Write a ZIP archive containing one CSV per entity type."""
        data = self.export_json()
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            for key in ["accounts", "categories", "budgets", "recurring_rules", "transactions"]:
                rows = data[key]
                if not rows:
                    continue
                buf = io.StringIO()
                writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
                zf.writestr(f"{key}.csv", buf.getvalue())

    # ── Import ────────────────────────────────────────────────────────────────

    def import_json(self, data: dict, mode: str) -> dict:
        """Import from a previously exported JSON dict.

        mode: 'merge' | 'replace'
        Returns stats dict with counts of created entities.
        """
        return self._import_data(
            accounts=data.get("accounts", []),
            categories=data.get("categories", []),
            budgets=data.get("budgets", []),
            recurring=data.get("recurring_rules", []),
            transactions=data.get("transactions", []),
            mode=mode,
        )

    def import_csv_zip(self, path: str, mode: str) -> dict:
        """Import from a ZIP archive of CSVs."""
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()

            def read_csv(fname):
                if fname not in names:
                    return []
                with zf.open(fname) as f:
                    reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"))
                    return list(reader)

            accounts = read_csv("accounts.csv")
            categories = read_csv("categories.csv")
            budgets = read_csv("budgets.csv")
            recurring = read_csv("recurring_rules.csv")
            transactions = read_csv("transactions.csv")

        # Coerce CSV string values to proper Python types
        for b in budgets:
            b["limit_amount"] = float(b.get("limit_amount") or 0)
        for c in categories:
            v = c.get("is_system", "0")
            c["is_system"] = str(v).strip() in ("1", "True", "true")
        for r in recurring:
            r["amount"] = float(r.get("amount") or 0)
            v = r.get("is_active", "1")
            r["is_active"] = str(v).strip() in ("1", "True", "true")
            for field in ("day_of_month", "day_of_week", "month_of_year"):
                raw = str(r.get(field, "")).strip()
                r[field] = int(raw) if raw and raw not in ("None", "null", "") else None
        for t in transactions:
            t["amount"] = float(t.get("amount") or 0)
            v = t.get("cleared", "0")
            t["cleared"] = str(v).strip() in ("1", "True", "true")
            raw = str(t.get("transfer_group", "")).strip()
            t["transfer_group"] = int(raw) if raw and raw not in ("None", "null", "") else None

        return self._import_data(accounts, categories, budgets, recurring, transactions, mode)

    # ── Private builders ──────────────────────────────────────────────────────

    def _build_accounts(self) -> list[dict]:
        return [
            {
                "name": a.name,
                "description": a.description,
                "account_type": a.account_type,
                "opening_balance": a.opening_balance,
            }
            for a in self._account_dao.get_all()
        ]

    def _build_categories(self) -> list[dict]:
        return [
            {
                "name": c.name,
                "type": c.type,
                "color_hex": c.color_hex,
                "is_system": c.is_system,
            }
            for c in self._category_dao.get_all()
        ]

    def _build_budgets(self) -> list[dict]:
        return [
            {
                "category_name": b.category_name,
                "month": b.month,
                "limit_amount": b.limit_amount,
            }
            for b in self._budget_dao.get_all()
        ]

    def _build_recurring(self) -> list[dict]:
        result = []
        for r in self._recurring_dao.get_all():
            result.append({
                "name": r.name,
                "type": r.type,
                "amount": r.amount,
                "account_name": r.account_name,
                "category_name": r.category_name,
                "description": r.description,
                "frequency": r.frequency,
                "start_date": r.start_date,
                "end_date": r.end_date,
                "day_of_month": r.day_of_month,
                "day_of_week": r.day_of_week,
                "month_of_year": r.month_of_year,
                "is_active": r.is_active,
            })
        return result

    def _build_transactions(self) -> list[dict]:
        all_txs = self._tx_dao.get_all()

        # Build account id → name map (one DB round-trip)
        acct_name_map = {a.id: a.name for a in self._account_dao.get_all()}

        # Build pair_map: pair_id → [tx, tx] sorted by id
        pair_map: dict[int, list] = {}
        for tx in all_txs:
            if tx.transfer_pair_id is not None:
                pair_map.setdefault(tx.transfer_pair_id, []).append(tx)
        for txs in pair_map.values():
            txs.sort(key=lambda t: t.id)

        # Assign sequential group numbers per pair
        pair_groups: dict[int, int] = {}
        counter = 0
        for pair_id in sorted(pair_map.keys()):
            counter += 1
            pair_groups[pair_id] = counter

        result = []
        for tx in all_txs:
            if tx.transfer_pair_id is not None:
                pair = pair_map.get(tx.transfer_pair_id, [])
                group = pair_groups.get(tx.transfer_pair_id)
                if len(pair) == 2:
                    role = "debit" if tx.id == pair[0].id else "credit"
                else:
                    role = "debit"
            else:
                group = None
                role = None

            result.append({
                "date": tx.date,
                "type": tx.type,
                "amount": tx.amount,
                "account_name": acct_name_map.get(tx.account_id, ""),
                "category_name": tx.category_name or "",
                "description": tx.description,
                "cleared": tx.cleared,
                "transfer_group": group,
                "transfer_role": role,
            })

        return result

    # ── Private import ────────────────────────────────────────────────────────

    def _import_data(
        self,
        accounts: list[dict],
        categories: list[dict],
        budgets: list[dict],
        recurring: list[dict],
        transactions: list[dict],
        mode: str,
    ) -> dict:
        stats = {
            "accounts": 0,
            "categories": 0,
            "budgets": 0,
            "recurring": 0,
            "transactions": 0,
        }

        conn = self._db.get_connection()

        # Replace mode: clear all user data in FK-safe order
        if mode == "replace":
            conn.execute("DELETE FROM transactions")
            conn.execute("DELETE FROM budgets")
            conn.execute("DELETE FROM recurring_rules")
            try:
                conn.execute("DELETE FROM dismissed_reminders")
            except Exception:
                pass  # Table may not exist on very old DBs
            conn.execute("DELETE FROM categories WHERE is_system = 0")
            conn.execute("DELETE FROM accounts")
            conn.commit()

        # Build name → id maps for existing entities
        existing_accts = {a.name: a.id for a in self._account_dao.get_all()}
        existing_cats = {c.name: c.id for c in self._category_dao.get_all()}

        # ── Accounts ──────────────────────────────────────────────────────────
        acct_map = dict(existing_accts)
        for a in accounts:
            name = (a.get("name") or "").strip()
            if not name:
                continue
            if name in acct_map:
                pass  # Already exists — skip in both merge and replace
            else:
                new_a = self._account_dao.create(
                    name,
                    a.get("description") or "",
                    a.get("account_type") or "checking",
                    float(a.get("opening_balance") or 0.0),
                )
                acct_map[name] = new_a.id
                stats["accounts"] += 1

        # ── Categories ────────────────────────────────────────────────────────
        cat_map = dict(existing_cats)
        for c in categories:
            name = (c.get("name") or "").strip()
            if not name:
                continue
            if name in cat_map:
                pass  # Already exists (system or user)
            else:
                new_c = self._category_dao.create(
                    name, c.get("type") or "both", c.get("color_hex") or "#888888"
                )
                cat_map[name] = new_c.id
                stats["categories"] += 1

        # ── Budgets ───────────────────────────────────────────────────────────
        for b in budgets:
            cat_name = (b.get("category_name") or "").strip()
            month = (b.get("month") or "").strip()
            try:
                limit = float(b.get("limit_amount") or 0)
            except (TypeError, ValueError):
                continue
            cat_id = cat_map.get(cat_name)
            if not cat_id or not month:
                continue
            if mode == "merge":
                existing = self._budget_dao.get_by_category_month(cat_id, month)
                if existing:
                    continue
            self._budget_dao.upsert(cat_id, month, limit)
            stats["budgets"] += 1

        # ── Recurring rules ───────────────────────────────────────────────────
        existing_recurring = {
            (r.name, r.account_id): r
            for r in self._recurring_dao.get_all()
        }
        for r in recurring:
            acct_name = (r.get("account_name") or "").strip()
            cat_name = (r.get("category_name") or "").strip()
            name = (r.get("name") or "").strip()
            acct_id = acct_map.get(acct_name)
            cat_id = cat_map.get(cat_name)
            if not acct_id or not cat_id or not name:
                continue
            if mode == "merge" and (name, acct_id) in existing_recurring:
                continue

            is_active = r.get("is_active", True)
            if not isinstance(is_active, bool):
                is_active = str(is_active).strip() in ("1", "True", "true")

            try:
                new_rule = self._recurring_dao.create(
                    name=name,
                    type_=r.get("type") or "expense",
                    amount=float(r.get("amount") or 0),
                    account_id=acct_id,
                    category_id=cat_id,
                    description=r.get("description") or "",
                    frequency=r.get("frequency") or "monthly",
                    start_date=r.get("start_date") or today_str(),
                    day_of_month=r.get("day_of_month"),
                    day_of_week=r.get("day_of_week"),
                    month_of_year=r.get("month_of_year"),
                    end_date=r.get("end_date") or None,
                )
                if not is_active:
                    self._recurring_dao.set_active(new_rule.id, False)
                stats["recurring"] += 1
            except Exception:
                pass

        # ── Transactions ──────────────────────────────────────────────────────
        # Build existing-tx key set for merge dedup
        existing_tx_keys: set[tuple] = set()
        if mode == "merge":
            for tx in self._tx_dao.get_all():
                existing_tx_keys.add(
                    (tx.account_id, tx.date, tx.type, tx.amount, tx.description)
                )

        non_transfers = [t for t in transactions if not t.get("transfer_group")]
        transfers = [t for t in transactions if t.get("transfer_group")]

        # Pass 1: non-transfer transactions
        for t in non_transfers:
            acct_name = (t.get("account_name") or "").strip()
            acct_id = acct_map.get(acct_name)
            if not acct_id:
                continue
            cat_name = (t.get("category_name") or "").strip()
            cat_id = cat_map.get(cat_name) if cat_name else None
            date_ = t.get("date") or ""
            type_ = t.get("type") or "expense"
            try:
                amount = float(t.get("amount") or 0)
            except (TypeError, ValueError):
                continue
            desc = t.get("description") or ""
            cleared = bool(t.get("cleared", False))

            if mode == "merge":
                key = (acct_id, date_, type_, amount, desc)
                if key in existing_tx_keys:
                    continue
                existing_tx_keys.add(key)

            try:
                self._tx_dao.create(
                    account_id=acct_id,
                    type_=type_,
                    amount=amount,
                    date=date_,
                    description=desc,
                    category_id=cat_id,
                    cleared=cleared,
                )
                stats["transactions"] += 1
            except Exception:
                pass

        # Pass 2: transfers — group by transfer_group int
        transfer_groups: dict[int, list] = {}
        for t in transfers:
            g = t.get("transfer_group")
            if g is not None:
                transfer_groups.setdefault(int(g), []).append(t)

        for group, txs in transfer_groups.items():
            if len(txs) != 2:
                continue
            debit = next((t for t in txs if t.get("transfer_role") == "debit"), txs[0])
            credit = next((t for t in txs if t.get("transfer_role") == "credit"), txs[1])

            from_acct_id = acct_map.get((debit.get("account_name") or "").strip())
            to_acct_id = acct_map.get((credit.get("account_name") or "").strip())
            if not from_acct_id or not to_acct_id:
                continue

            date_ = debit.get("date") or ""
            try:
                amount = float(debit.get("amount") or 0)
            except (TypeError, ValueError):
                continue
            desc = debit.get("description") or ""

            if mode == "merge":
                key = (from_acct_id, date_, "transfer", amount, desc)
                if key in existing_tx_keys:
                    continue

            try:
                self._tx_svc.create_transfer(from_acct_id, to_acct_id, amount, date_, desc)
                stats["transactions"] += 2
            except Exception:
                pass

        return stats
