"""
Parsing logic for the incentive spreadsheet.

Nothing in this module talks to Google: it works on plain grids of values,
so it can be unit-tested and reused with any data source.

Everything is found by header text, not by column letter, so the app keeps
working when columns move or when month names change every quarter.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

SALARY_ONLY_MARKER = "only for salary calculation"
FULL = 0.9999  # anything at or above this counts as 100%

# ---------------------------------------------------------------- ACH config

# Columns shown in the dashboard, in this order.
ACH_COLUMNS = [
    "Merchant Name",
    "Amount paid for",
    "Final Amount paid for",
    "Zoho DPAY ID",
    "Deal Ref ID",
    "Formula Invoice Value",
    "Gross Margin",
    "Live Gross Margin",
    "Rista Gross Margin",
    "Live %",
    "QR Live %",
]
REMAINING_EXTRA = ["Difference %", "New Live Gross Margin"]

# Other spellings accepted for each column (compared without spaces/case).
ALIASES = {
    "Live %": ["Live %", "Live %age", "Live Percentage", "LIVE %"],
    "QR Live %": ["QR Live %", "QR LIVE %", "QR Live %age", "QR Live Percentage"],
    "Live Gross Margin": ["Live Gross Margin", "Live GM"],
    "Rista Gross Margin": ["Rista Gross Margin", "Rista GM", "RISTA_GM"],
    "Zoho DPAY ID": ["Zoho DPAY ID", "Zoho Payment ID", "Payment ID."],
    "Deal Ref ID": ["Deal Ref ID", "DRF ID"],
    "Formula Invoice Value": ["Formula Invoice Value", "Invoice Value"],
    "Difference %": ["Difference %", "Difference"],
    "New Live Gross Margin": ["New Live Gross Margin", "New Live GM"],
}

# Column that holds the salesperson's email in the ACH tabs (first one found wins).
OWNER_HEADERS = ["POC", "BDM", "Actual Owner", "Actual Owner Email ID", "SPOC Email", "Owner"]

NUMERIC_COLUMNS = {
    "Formula Invoice Value", "Gross Margin", "Live Gross Margin", "Rista Gross Margin",
    "Live %", "QR Live %", "Difference %", "New Live Gross Margin",
}
SUM_COLUMNS = ["Formula Invoice Value", "Gross Margin", "Live Gross Margin",
               "Rista Gross Margin", "New Live Gross Margin"]

# ------------------------------------------------------------------- helpers


def clean(v) -> str:
    return re.sub(r"\s+", " ", str(v if v is not None else "")).strip()


def key(v) -> str:
    """Comparison form of a header: lowercase, no spaces/underscores, common typos fixed."""
    s = clean(v).lower().replace("\u2019", "'")
    s = s.replace("quaterly", "quarterly").replace("percentage", "%").replace("%age", "%")
    return re.sub(r"[\s_]+", "", s)


def is_email(v) -> bool:
    s = str(v or "")
    return "@" in s and "." in s.split("@")[-1]


def to_number(v) -> float | None:
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "").replace("₹", "").replace(" ", "")
    if s in ("", "-", "—"):
        return None
    pct = s.endswith("%")
    try:
        n = float(s.rstrip("%"))
    except ValueError:
        return None
    return n / 100 if pct else n


def to_pct(v) -> float | None:
    """Returns a fraction (1.0 = 100%). Accepts 1, 0.75, '75%', or 75."""
    n = to_number(v)
    if n is None:
        return None
    return n / 100 if n > 1.5 else n


def inr(n: float) -> str:
    sign = "-" if n < 0 else ""
    return f"{sign}₹{abs(n):,.0f}"


def col_letter(idx0: int) -> str:
    s, n = "", idx0 + 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def a1(title: str, r0: int, c0: int) -> str:
    return "'" + title.replace("'", "''") + f"'!{col_letter(c0)}{r0 + 1}"


def period_from(text: str) -> str:
    m = re.search(r"\(([^()]*)\)", text or "")
    return clean(m.group(1)) if m else ""


@dataclass
class Grid:
    title: str
    display: list  # formatted values, as people see them in the sheet
    raw: list      # unformatted values, used for maths and comparisons

    @property
    def nrows(self) -> int:
        return len(self.display)

    def d(self, r: int, c: int) -> str:
        try:
            return clean(self.display[r][c])
        except IndexError:
            return ""

    def v(self, r: int, c: int):
        try:
            return self.raw[r][c]
        except IndexError:
            return ""

    def width(self, r: int) -> int:
        return len(self.display[r]) if 0 <= r < self.nrows else 0


# ----------------------------------------------------------------- main tab

MAIN_FIELD_RULES = [
    ("salaryQ", lambda k: k == "quarterlysalary"),
    ("leads", lambda k: k == "quarterlyleads"),
    ("mktg", lambda k: k.startswith("shareofmktg")),
    ("gm", lambda k: k == "quarterlygrossmargin"),
    ("rista", lambda k: k == "ristagross"),
    ("egm", lambda k: k == "egm" or k.startswith("egm(")),
    ("liveGm", lambda k: k == "livegm"),
    ("liveEgm", lambda k: k == "liveegm"),
    ("egmBucket", lambda k: k == "egmbucket"),
    ("ristaPct", lambda k: k.startswith("rista%togm")),
    ("ristaBucket", lambda k: k.startswith("rista%bucket")),
    ("slabRista", lambda k: k.startswith("%slab(")),
    ("slab", lambda k: k == "%slab"),
    ("prevIncentive", lambda k: k.startswith("incentiveamount") and k != "incentiveamount"),
    ("incentive", lambda k: k == "incentiveamount"),
    ("refunds", lambda k: k == "refunds"),
    ("prevGm", lambda k: "livegrossmargin" in k),
    ("total", lambda k: k.startswith("totalamount")),
]


@dataclass
class Table:
    kind: str                 # "BDM" or "HEAD" (Enterprise City Heads / managers)
    title: str
    header_row: int
    first_col: int
    last_col: int
    email_col: int
    headers: list
    fields: dict
    salary_cols: list
    month_labels: list
    rows: list = field(default_factory=list)
    salary_only_rows: set = field(default_factory=set)

    @property
    def team(self) -> str:
        return clean(self.title.split("(")[0].replace("_", " "))


@dataclass
class Match:
    table: Table
    row: int
    extra_salary_cells: list  # (row, col) also holding this person's salary


def find_tables(g: Grid) -> list[Table]:
    tables = []
    for r in range(g.nrows):
        for c in range(g.width(r)):
            k = key(g.d(r, c))
            if k in ("bdm", "manager"):
                t = _build_table(g, r, c, "BDM" if k == "bdm" else "HEAD")
                if t:
                    tables.append(t)
    return tables


def _build_table(g: Grid, r: int, c: int, kind: str) -> Table | None:
    first = c
    while first > 0 and g.d(r, first - 1):
        first -= 1
    last = c
    while g.d(r, last + 1):
        last += 1

    headers = [g.d(r, i) for i in range(first, last + 1)]
    fields, salary_cols, months = {}, [], []
    for i, h in enumerate(headers):
        k = key(h)
        col = first + i
        if "salary" in k and k != "quarterlysalary":
            salary_cols.append(col)
            months.append(clean(re.sub(r"salary", "", h, flags=re.I)))
            continue
        for name, rule in MAIN_FIELD_RULES:
            if name not in fields and rule(k):
                fields[name] = col
                break
    if not salary_cols:
        return None

    title = ""
    if r > 0:
        title = next((g.d(r - 1, i) for i in range(first, last + 1) if g.d(r - 1, i)), "")

    t = Table(kind, title, r, first, last, c, headers, fields, salary_cols, months)
    rr = r + 1
    while rr < g.nrows and is_email(g.d(rr, c)):
        t.rows.append(rr)
        row_text = " ".join(g.d(rr, i).lower() for i in range(first, last + 1))
        if SALARY_ONLY_MARKER in row_text:
            t.salary_only_rows.add(rr)
        rr += 1
    return t


def locate(g: Grid, tables: list[Table], email: str) -> Match | None:
    """Find the person's row. Managers (City Heads table) take priority; BDM rows marked
    "Only for Salary Calculation" are never returned as a statement."""
    email = email.strip().lower()

    def same(t: Table, r: int) -> bool:
        return g.d(r, t.email_col).lower() == email

    for t in tables:
        if t.kind != "HEAD":
            continue
        for r in t.rows:
            if same(t, r):
                extra = [(br, c) for b in tables if b.kind == "BDM"
                         for br in b.rows if same(b, br) for c in b.salary_cols]
                return Match(t, r, extra)
    for t in tables:
        if t.kind == "BDM":
            for r in t.rows:
                if r not in t.salary_only_rows and same(t, r):
                    return Match(t, r, [])
    return None


def name_from_email(email: str) -> str:
    local = re.sub(r"\d+", "", email.split("@")[0])
    return " ".join(p.capitalize() for p in re.split(r"[._-]", local) if p)


def statement(g: Grid, m: Match) -> dict:
    t, r = m.table, m.row
    f = {k: g.d(r, c) for k, c in t.fields.items()}
    salaries = []
    for c in t.salary_cols:
        n = to_number(g.v(r, c))
        salaries.append(n if n is not None else 0)
    details = [
        {"label": t.headers[i], "value": g.d(r, t.first_col + i)}
        for i in range(len(t.headers))
        if t.first_col + i != t.email_col
    ]
    return {
        "role": "Manager" if t.kind == "HEAD" else "BDM",
        "team": t.team,
        "period": period_from(t.title),
        "months": t.month_labels,
        "salaries": salaries,
        "f": f,
        "details": details,
        "ledger": ledger(f),
    }


def _has(v) -> bool:
    return clean(v) not in ("", "-")


def ledger(f: dict) -> list[dict]:
    slab = f.get("slabRista") if _has(f.get("slabRista")) else f.get("slab", "")
    rista = ""
    if _has(f.get("ristaPct")):
        rista = f"Rista share of gross margin: {f['ristaPct']}"
        if _has(f.get("ristaBucket")):
            rista += f" ({f['ristaBucket']})"
    lines = [
        ("", "Quarterly gross margin", "", f.get("gm"), ""),
        ("−", "Quarterly salary", "Total of the three months you entered", f.get("salaryQ"), ""),
        ("−", "Marketing cost share", "", f.get("mktg"), "") if _has(f.get("mktg")) else None,
        ("+", "Refund adjustment", "Negative when refunds were deducted", f.get("refunds"), ""),
        ("=", "Effective gross margin (EGM)",
         f"EGM bucket: {f['egmBucket']}" if _has(f.get("egmBucket")) else "", f.get("egm"), "sum"),
        ("", "Live EGM", "EGM from cases that have gone live", f.get("liveEgm"), ""),
        ("×", "Incentive slab", rista, slab, ""),
        ("=", "Incentive for this quarter", "Live EGM × slab", f.get("incentive"), "sum"),
        ("+", "Last quarter’s cases that went live",
         f"Incentive on {f['prevGm']} live gross margin" if _has(f.get("prevGm")) else "",
         f.get("prevIncentive"), ""),
        ("=", "Total payout", "", f.get("total"), "grand"),
    ]
    out = []
    for line in lines:
        if not line:
            continue
        op, label, note, val, cls = line
        val = val if _has(val) else "—"
        out.append({"op": op, "label": label, "note": note, "value": val, "cls": cls,
                    "neg": str(val).strip().startswith("-")})
    return out


# ------------------------------------------------------------------ ACH tabs


def find_columns(headers: list[str], names: list[str]) -> dict:
    keys = [key(h) for h in headers]
    out = {}
    for name in names:
        for alias in ALIASES.get(name, [name]):
            k = key(alias)
            if k in keys:
                out[name] = keys.index(k)
                break
    return out


def find_header_row(g: Grid, names: list[str], scan: int = 10) -> int:
    best, best_n = 0, -1
    for r in range(min(scan, g.nrows)):
        n = len(find_columns([g.d(r, c) for c in range(g.width(r))], names))
        if n > best_n:
            best, best_n = r, n
    return best


def ach_cases(g: Grid, email: str, columns: list[str]) -> dict:
    """Rows of an ACH tab that belong to `email`, with the requested columns."""
    hr = find_header_row(g, columns + OWNER_HEADERS)
    headers = [g.d(hr, c) for c in range(g.width(hr))]
    cols = find_columns(headers, columns)
    owner = find_columns(headers, OWNER_HEADERS)
    owner_col = next((owner[h] for h in OWNER_HEADERS if h in owner), None)
    missing = [c for c in columns if c not in cols]
    if owner_col is None:
        return {"rows": [], "missing": missing, "owner_missing": True}

    email = email.strip().lower()
    rows = []
    for r in range(hr + 1, g.nrows):
        if clean(g.d(r, owner_col)).lower() != email:
            continue
        cells, raw = [], {}
        for name in columns:
            c = cols.get(name)
            cells.append(g.d(r, c) if c is not None else "")
            raw[name] = g.v(r, c) if c is not None else ""
        live = to_pct(raw.get("Live %"))
        qr = to_pct(raw.get("QR Live %"))
        rows.append({
            "cells": cells,
            "raw": raw,
            "live": 0.0 if live is None else live,  # blank Live % = not live yet
            "qr": qr,                               # blank QR Live % = not applicable
        })
    return {"rows": rows, "missing": missing, "owner_missing": False}


def is_fully_live(row: dict) -> bool:
    return row["live"] >= FULL and (row["qr"] is None or row["qr"] >= FULL)


def totals(rows: list[dict], columns: list[str]) -> list[str]:
    out = []
    for name in columns:
        if name in SUM_COLUMNS:
            s = sum(to_number(r["raw"].get(name)) or 0 for r in rows)
            out.append(inr(s))
        else:
            out.append("")
    return out


def column_meta(columns: list[str]) -> list[dict]:
    ids = {"Zoho DPAY ID", "Deal Ref ID"}
    return [{"name": c, "numeric": c in NUMERIC_COLUMNS, "nowrap": c in ids} for c in columns]


# --------------------------------------------------------------- tab names

MONTHS = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]


def resolve_tab(tabs: list[tuple[str, bool]], pattern: str, prefer_months: list[str] | None = None):
    """Pick the tab whose name matches `pattern`. Visible tabs win over hidden ones,
    then tabs whose name mentions the preferred months (the current quarter)."""
    rx = re.compile(pattern, re.I)
    cands = [(t, h) for t, h in tabs if rx.search(clean(t.replace("_", " ")))]
    if not cands:
        return None

    def score(item):
        t, hidden = item
        months = sum(1 for m in (prefer_months or []) if m in t.lower())
        return (0 if hidden else 1, months)

    return max(cands, key=score)[0]


def months_in(text: str) -> list[str]:
    low = (text or "").lower()
    return [m for m in MONTHS if m in low]
