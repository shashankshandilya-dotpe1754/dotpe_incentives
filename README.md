# Sales Incentive Portal (Python + HTML)

A small Flask web app on top of the incentive Google Sheet. Each salesperson signs in with their dotpe.in Google account. They then see only their own row from the Quarterly Incentive tab and can enter their three monthly salaries. The sheet's own formulas recalculate the incentive, and the app shows the result.

The dashboard also lists that person's own cases from:

- **Combined ACH** (this quarter), split into **100% live** and **Below 100% live**
- **Remaining ACH** (last quarter), showing only cases still below 100% live, plus Difference % and New Live Gross Margin

Backend tabs (Mapping, Refund, Marketing Cost, LIVE/NOT_LIVE, and so on) are never shown. Salespeople never get access to the sheet itself.

## Try it locally in 1 minute (sample data, no Google setup)

```bash
pip install -r requirements.txt
DEMO_MODE=1 COOKIE_SECURE=0 python app.py
# open http://localhost:5000 and pick a sample person
```

## Real setup

### 1. Google Cloud project (one time)
1. In console.cloud.google.com, create a project and enable the **Google Sheets API**.
2. **Service account** (the app uses it to read and write the sheet): go to IAM & Admin → Service Accounts → Create, then Keys → Add key → JSON. Save the file as `service-account.json` next to `app.py`.
3. Open the Google Sheet → Share → add the service account's email (…@….iam.gserviceaccount.com) as **Editor**. Editor access is needed because the app writes salaries.
4. **Sign-in**: go to APIs & Services → OAuth consent screen and choose **Internal**, so only dotpe.in accounts can sign in. Then go to Credentials → Create OAuth client ID → Web application, and add the redirect URI `https://YOUR-DOMAIN/auth/callback` (and `http://localhost:5000/auth/callback` for testing).

### 2. Configure
Copy `.env.example` to `.env` and fill in `SECRET_KEY`, `SPREADSHEET_ID`, `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.

### 3. Run
```bash
pip install -r requirements.txt
gunicorn -w 1 --threads 8 -b 0.0.0.0:8000 app:app
```
Put it behind HTTPS (Cloud Run, a VM with nginx, Render, or similar). Use **one worker**: salary saves are serialised with an in-process lock.

## Every quarter

You don't need to change anything as long as the new tabs keep the same naming style:

| Tab | Matched by (case-insensitive) | If more than one matches |
|---|---|---|
| Main | name starts with `Quaterly Incentive` / `Quarterly Incentive` | visible tab wins |
| Combined ACH | name starts with `Combined ACH` | visible tab wins, then the one naming this quarter's months |
| Remaining ACH | name starts with `Remaining ACH` | visible tab wins |

Month names in salary headers (e.g. `October'2026 Salary`) are read from the sheet, so they update on their own. If a match ever picks the wrong tab, hide the old tab or set `MAIN_TAB_NAME`, `COMBINED_TAB_NAME` or `REMAINING_TAB_NAME` in `.env`. When the salary deadline passes, set `EDITS_OPEN=0`.

## What the sheet must contain

**Main tab.** Tables with a header cell `BDM` (SMB, Inbound, Enterprise) and a header cell `Manager` (Enterprise City Heads). Columns are found by header text, so their order doesn't matter:

- Monthly salaries: any header containing "Salary" except "Quarterly Salary".
- Rows marked **Only for Salary Calculation** are never shown as an incentive.
- Managers see their City Heads row. Their salary is written to both their City Heads row and their "Only for Salary Calculation" row. Any cell that holds a formula is skipped, so linked cells are never overwritten.

**Combined ACH and Remaining ACH.** Headers needed (other spellings in brackets are also accepted):

`Merchant Name`, `Amount paid for`, `Final Amount paid for`, `Zoho DPAY ID` (Payment ID.), `Deal Ref ID` (DRF ID), `Formula Invoice Value` (Invoice Value), `Gross Margin`, `Live Gross Margin` (Live GM), `Rista Gross Margin` (RISTA_GM), `Live %` (Live %age, Live Percentage), `QR Live %`. Remaining ACH also needs `Difference %` (Difference) and `New Live Gross Margin`.

Both tabs also need a column with the **salesperson's email**, so each person only sees their own cases. The first of these found is used: `POC`, `BDM`, `Actual Owner`, `Actual Owner Email ID`, `SPOC Email`, `Owner`. To add another spelling, edit `ALIASES` or `OWNER_HEADERS` in `incentives.py`.

**Live rules:** a case is 100% live when Live % is 100% **and** QR Live % is 100%. A blank QR Live % means QR doesn't apply. A blank Live % counts as not live yet.

## Security
- The signed-in email comes from Google and is checked on the server. It must be a verified dotpe.in address **and** appear in the main tab.
- The server reads the sheet and sends the browser only that person's rows. Other people's data never leaves the server.
- Salary saves need a CSRF token. Values are validated (0 to `MAX_MONTHLY_SALARY`) and every change is recorded in a **Salary Audit Log** tab.
- Pages are sent with `no-store`, so pay data isn't cached by the browser.

## Files
| File | What it does |
|---|---|
| `app.py` | Routes, Google sign-in, salary API |
| `service.py` | Builds one person's dashboard, saves salaries, caches sheet reads (60 s) |
| `incentives.py` | Reads tables and columns by header text, applies the 100% live rules |
| `sheets.py` | Google Sheets access (service account) and the demo data source |
| `templates/`, `static/` | HTML, CSS, JS |
| `tests/` | `python -m pytest -q tests` |
