# New Budget App — User Guide

## Getting Started

Launch the app with `python main.py`. On first run the database is created automatically. Each calendar year gets its own database file (`budget_2026.db`, etc.).

### Accounts

All activity is scoped to an **account** selected from the dropdown in the top bar. To add or manage accounts, click the **Accounts** button next to the dropdown.

**Account types:**

| Type | Description |
|---|---|
| Checking | Standard account; shows running balance |
| Savings | Standard account; shows running balance |
| Loan | Debt account; shows amount owed |
| Credit Card | Debt account; shows amount owed |

When you create a **Loan** or **Credit Card** account, set the **Opening Balance** to the initial amount owed. The app tracks your payoff progress from there.

---

## Tabs

### Dashboard

A monthly snapshot of the selected account.

- Use **◀ ▶** to navigate months.
- **Summary cards** show Income / Expenses / Net (or for debt accounts: Amount Owed / Charges / Payments).
- **Recent Transactions** lists the last 10 entries with running balance.
- **Budget Progress** shows each category's spending vs. its limit with color-coded bars: green (safe) → orange (near limit) → red (over limit).

---

### Register

The full transaction ledger for the selected account.

**Filter bar** — narrow the list by month, transaction type (Income / Expense / Transfer), cleared status, or a keyword search.

**Adding transactions:**

| Button | Creates |
|---|---|
| + Income | Deposit or income entry |
| + Expense | Spending entry |
| + Transfer | Moves money between accounts |
| + Charge *(debt accounts)* | Purchase on a loan or card |
| Make Payment *(debt accounts)* | Payment from another account to this debt |

**Columns:**

- **✓** — Cleared checkbox. Click to toggle; saves immediately.
- **Type** — Color-coded: green = income, red = expense, blue = transfer.
- **Balance / Amt Owed** — Running balance for standard accounts; amount still owed for debt accounts.
- **Edit / Delete** — Edit any field on a transaction, or remove it. Deleting either side of a transfer removes both sides.

---

### Budgets

Set monthly spending limits by category.

- Navigate months with **◀ ▶**.
- **+ Add Budget** — Pick a category and enter a monthly limit.
- **Copy from Previous Month** — Pulls all limits from the prior month (useful at the start of a new month).
- Budget limits from December carry over automatically into all months of the new year.

Each budget card shows the amount spent, the limit, and how much remains. The progress bar turns orange near the limit and red when exceeded. Dashboard mirrors these progress bars.

---

### Recurring

Automate regular transactions such as paychecks, rent, or subscriptions.

**+ Add Rule** — Set the name, type (income or expense), amount, account, category, frequency, start date, and an optional end date.

**Frequencies:**

| Frequency | Scheduling option |
|---|---|
| Monthly | Day of month: 1–28 or **Last** (last day of the month) |
| Weekly | Day of week: Mon–Sun |
| Every 2 Weeks | Day of week: Mon–Sun |
| Every 3 Weeks | Day of week: Mon–Sun |
| Every 4 Weeks | Day of week: Mon–Sun |
| Yearly | Month (1–12) and day (1–28 or **Last**) |

Rules run automatically every time the app starts. If a rule was missed, the app catches up the last 90 days. Use the **Pause / Resume** toggle to temporarily disable a rule without deleting it. To remove a rule permanently, open **Edit** and click **Delete**.

---

### Reports

Analyze income and expenses for any account and month.

- Select **All Accounts** or a specific account from the dropdown.
- Navigate months with **◀ ▶**.
- **Summary cards** show totals for the selected month.
- **Bar chart** shows 6 months of income vs. expenses side by side.
- **Pie chart** breaks down the top 8 expense categories.
- **Export CSV** saves the current month's transactions to a file.

---

### Forecast

Project future income and expenses.

**Forecast source** — Choose what data to base projections on:

| Option | Uses |
|---|---|
| Recurring Only | Active recurring rules only |
| Recurring + Budgets | Recurring rules plus monthly budget limits |
| Recurring + History | Recurring rules plus historical averages *(default)* |

**View modes:**

- **Monthly** — Month-by-month through December of next year. Scroll horizontally to see all months.
- **Annual** — Year-by-year for 10 years.

The bar chart shows projected income (green) and expenses (red). The summary table shows Income, Expense, and Net per period; negative net is highlighted in red.

---

### Net Worth

A snapshot of your overall financial position across all accounts.

- **Headline card** — Current net worth (green if positive, red if negative), updated as of the current month.
- **Assets panel** — All checking and savings accounts with their current balances and a running total.
- **Liabilities panel** — All loan and credit card accounts with their current amount owed and a running total.
- **History toggle** — Switch between **12 months** and **24 months** of historical net worth.
- **Bar chart** — Month-by-month net worth trend; green bars above zero, red bars below.

---

### Categories

Manage the categories used when entering transactions.

- **+ Add Category** — Set a name, type (Expense / Income / Both), and color.
- **Edit** — Change the name, type, or color of any user-created category.
- **Delete** — Available for user-created categories only. Existing transactions keep their label, but the category won't appear in future dropdowns.

System categories (seeded on first run) cannot be deleted.

---

### Settings

#### Database Folder
Change where the app stores its `budget_YYYY.db` files. Use **Browse** to pick a folder, or **Reset to Default** to go back to the app directory. Takes effect after restarting the app.

#### Export / Import

| Action | Format | Description |
|---|---|---|
| Export JSON | `.json` | All data in a single file |
| Export CSV ZIP | `.zip` | One CSV per table (spreadsheet-friendly) |
| Import JSON | `.json` | Restore or merge from a JSON export |
| Import CSV ZIP | `.zip` | Restore or merge from a CSV ZIP export |

**Import modes:**
- **Merge** — Adds or updates imported records while keeping existing data.
- **Replace** — Wipes the current database and restores entirely from the import file. Use with caution.

#### App Settings

| Setting | Options |
|---|---|
| Appearance | System (follows OS) · Light · Dark |
| Currency Symbol | Any symbol — `$`, `€`, `£`, etc. |
| Date Format | MM/DD/YYYY · DD/MM/YYYY · YYYY-MM-DD |

Date format and DB folder changes require an app restart. All other settings apply immediately.

---

## Reminders

On startup, the app may show a **Reminder Dialog** listing items that need attention — such as overdue recurring rules or over-budget categories. Each reminder can be dismissed individually with the **✕** button, or you can dismiss all at once with **OK, Dismiss All**. Dismissed reminders won't reappear until their expiry date.

---

## Transfers

A transfer between two accounts creates a linked pair of transactions:

- The **source account** (from) shows a negative (red) entry.
- The **destination account** (to) shows a positive (green) entry.

Both sides are visible in their respective account registers. Deleting either side removes both.

**Paying a credit card or loan:**
In the debt account's Register, click **Make Payment**. Select the source account and amount. The app creates a transfer that reduces the amount owed on the debt account.

---

## Tips

- The **cleared checkbox** in Register auto-saves — no need to open the edit form just to mark a transaction cleared.
- The account dropdown at the top persists your selection as you switch tabs.
- Budgets tab → **Copy from Previous Month** is the fastest way to set up a new month.
- Use **Forecast → Recurring + History** for the most realistic projection once you have a few months of data.
- Export a JSON backup periodically from Settings before making large imports or changes.
