# New Budget

A personal finance desktop application built with Python and CustomTkinter. Track spending across multiple accounts, set monthly budgets, automate recurring transactions, and visualize your financial health — all stored locally with no accounts or cloud services required.

## Features

- **Dashboard** — per-account summary of income, expenses, and current balance
- **Register** — scrollable transaction ledger with running balance; supports income, expense, and transfer entries
- **Budgets** — monthly category spending limits with configurable alert thresholds
- **Recurring transactions** — automated rules for regular income/expenses on weekly, bi-weekly, monthly, or yearly schedules, with last-day-of-month support; missed entries are caught up automatically (up to 90 days back)
- **Reports** — bar and pie charts of spending and income by category for any date range
- **Forecast** — projected cash flow using recurring rules and budget data; monthly and annual views
- **Net Worth** — historical net worth chart across all accounts
- **Categories** — custom income/expense categories with color coding
- **Settings** — appearance mode, currency symbol, date format, and database folder location
- **Data export/import** — full backup and restore as JSON or CSV-in-ZIP
- **Startup reminders** — alerts for upcoming recurring transactions and budget thresholds approaching the limit

## Account types

| Type | Behavior |
|---|---|
| Checking | Standard asset account |
| Savings | Standard asset account |
| Loan | Debt account — tracks amount owed |
| Credit Card | Debt account — tracks amount owed |

Debt accounts display dedicated **+ Charge** and **Make Payment** buttons in the register. Transfers between accounts are recorded atomically as a matching pair of rows.

## Requirements

- Python 3.11+
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
- [tkcalendar](https://github.com/j4321/tkcalendar)
- [Pillow](https://python-pillow.org/)
- [matplotlib](https://matplotlib.org/)

## Installation

```bash
git clone <repo-url>
cd budget
pip install customtkinter tkcalendar pillow matplotlib
```

## Usage

```bash
python main.py
```

The database is created automatically on first run. Each calendar year gets its own SQLite file (`budget_YYYY.db`). Budget limits are carried over from the previous year automatically at the start of a new year.

The database folder defaults to the project directory and can be changed from the **Settings** tab. The folder preference is stored in `~/.budget/config.json` independently of the database so it persists across database changes.

## Project structure

```
newbudget/
├── main.py                  # Entry point and dependency injection root
├── database/
│   ├── db_manager.py        # Schema, migrations, and year-keyed DB factory
│   ├── account_dao.py
│   ├── transaction_dao.py
│   ├── budget_dao.py
│   ├── category_dao.py
│   ├── recurring_dao.py
│   └── dismissed_reminder_dao.py
├── models/                  # Plain dataclasses (Account, Transaction, …)
├── services/                # Business logic layer
│   ├── account_service.py
│   ├── transaction_service.py
│   ├── budget_service.py
│   ├── recurring_service.py
│   ├── report_service.py
│   ├── forecast_service.py
│   ├── net_worth_service.py
│   ├── reminder_service.py
│   ├── category_service.py
│   └── data_service.py      # Export / import
├── ui/
│   ├── app_window.py        # Main window, tab bar, account selector
│   ├── tabs/                # One file per tab
│   └── components/          # Shared forms and widgets
└── utils/
    ├── app_config.py        # Pre-database config (~/.budget/config.json)
    ├── date_helpers.py
    ├── currency.py
    └── constants.py
```

## Architecture

The app follows a strict three-layer architecture with dependency injection. The UI never calls DAOs directly.

```
UI (tabs + forms)  →  Services (business logic)  →  DAOs (SQL)  →  DatabaseManager (SQLite)
```

All dependencies are wired in `main.py`. Every class receives its dependencies via constructor — no singletons or global state.

## License

MIT
