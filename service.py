"""
Builds one person's dashboard and saves their salary.
Every method takes the signed-in email and only ever returns that person's rows.
"""
from __future__ import annotations

import threading
import time

import incentives as inc
from sheets import now_str


class PortalError(Exception):
    """A problem the person can act on; the message is shown to them."""


class Portal:
    def __init__(self, source, cfg):
        self.src = source
        self.cfg = cfg
        self._cache = None
        self._cache_at = 0.0
        self._lock = threading.Lock()

    # ------------------------------------------------------------- data access

    def _resolve_tabs(self) -> dict:
        tabs = self.src.tabs()
        cfg = self.cfg
        main = cfg.MAIN_TAB_NAME or inc.resolve_tab(tabs, cfg.MAIN_TAB_PATTERN)
        if not main:
            raise RuntimeError("Main incentive tab not found. Check MAIN_TAB_PATTERN.")
        return {
            "main": main,
            "combined": cfg.COMBINED_TAB_NAME or None,
            "remaining": cfg.REMAINING_TAB_NAME or inc.resolve_tab(tabs, cfg.REMAINING_TAB_PATTERN),
            "_all": tabs,
        }

    def _data(self, fresh: bool = False) -> dict:
        if not fresh and self._cache and time.time() - self._cache_at < self.cfg.CACHE_SECONDS:
            return self._cache
        names = self._resolve_tabs()
        main = self.src.read([names["main"]])[names["main"]]
        tables = inc.find_tables(main)
        if not tables:
            raise RuntimeError(f"No BDM tables found in tab '{names['main']}'.")

        period = inc.period_from(tables[0].title)
        if not names["combined"]:
            names["combined"] = inc.resolve_tab(names["_all"], self.cfg.COMBINED_TAB_PATTERN,
                                                inc.months_in(period))
        extra = [n for n in (names["combined"], names["remaining"]) if n]
        grids = self.src.read(extra) if extra else {}
        self._cache = {"names": names, "main": main, "tables": tables, "grids": grids}
        self._cache_at = time.time()
        return self._cache

    def invalidate(self):
        self._cache = None

    # --------------------------------------------------------------- dashboard

    def dashboard(self, email: str) -> dict | None:
        email = email.strip().lower()
        data = self._data()
        match = inc.locate(data["main"], data["tables"], email)
        if not match:
            return None
        stmt = inc.statement(data["main"], match)
        stmt.update(email=email, name=inc.name_from_email(email), editsOpen=self.cfg.EDITS_OPEN)
        return {
            "stmt": stmt,
            "combined": self._combined(data, email),
            "remaining": self._remaining(data, email),
        }

    def _section(self, data, which, columns, email):
        name = data["names"].get(which)
        if not name or name not in data["grids"]:
            return None, {"found": False, "columns": inc.column_meta(columns)}
        res = inc.ach_cases(data["grids"][name], email=email, columns=columns)
        base = {
            "found": True,
            "tab": name,
            "period": inc.period_from(name),
            "columns": inc.column_meta(columns),
            "missing": res["missing"],
            "owner_missing": res["owner_missing"],
        }
        return res["rows"], base

    def _combined(self, data, email):
        cols = inc.ACH_COLUMNS
        rows, out = self._section(data, "combined", cols, email)
        if rows is None:
            return out
        full = [r for r in rows if inc.is_fully_live(r)]
        part = [r for r in rows if not inc.is_fully_live(r)]
        out["groups"] = [
            {"id": "full", "label": "100% live", "rows": full, "totals": inc.totals(full, cols)},
            {"id": "partial", "label": "Below 100% live", "rows": part, "totals": inc.totals(part, cols)},
        ]
        return out

    def _remaining(self, data, email):
        cols = inc.ACH_COLUMNS + inc.REMAINING_EXTRA
        rows, out = self._section(data, "remaining", cols, email)
        if rows is None:
            return out
        below = [r for r in rows if not inc.is_fully_live(r)]
        out["rows"] = below
        out["totals"] = inc.totals(below, cols)
        return out

    # ------------------------------------------------------------ save salary

    def _validate(self, values, months) -> list[float]:
        if not isinstance(values, list) or len(values) != len(months):
            raise PortalError(f"Enter a salary for each of the {len(months)} months.")
        out = []
        for v, m in zip(values, months):
            s = str(v if v is not None else "").replace(",", "").replace("₹", "").strip()
            try:
                n = float(s) if s else 0.0
            except ValueError:
                raise PortalError(f"{m}: enter a number, like 45000.")
            if n != n or n < 0:
                raise PortalError(f"{m}: enter an amount of zero or more.")
            if n > self.cfg.MAX_MONTHLY_SALARY:
                raise PortalError(f"{m}: {inc.inr(n)} is above the {inc.inr(self.cfg.MAX_MONTHLY_SALARY)} "
                                  "monthly limit. Check the amount.")
            out.append(round(n, 2))
        return out

    def save_salaries(self, email: str, values) -> None:
        if not self.cfg.EDITS_OPEN:
            raise PortalError("Salary entry is closed for this quarter. Contact sales ops to make changes.")
        email = email.strip().lower()
        if not self._lock.acquire(timeout=30):
            raise PortalError("The sheet is busy. Try saving again in a few seconds.")
        try:
            data = self._data(fresh=True)
            g = data["main"]
            m = inc.locate(g, data["tables"], email)
            if not m:
                raise PortalError("Your email isn’t in the incentive sheet.")
            vals = self._validate(values, m.table.month_labels)
            before = [inc.to_number(g.v(m.row, c)) or 0 for c in m.table.salary_cols]

            targets = [(m.row, c, vals[i]) for i, c in enumerate(m.table.salary_cols)]
            n = len(m.table.salary_cols)
            targets += [(r, c, vals[i % n]) for i, (r, c) in enumerate(m.extra_salary_cells)]

            cells = [inc.a1(g.title, r, c) for r, c, _ in targets]
            formulas = self.src.formulas(cells)
            updates = [(a, v) for a, f, (_, _, v) in zip(cells, formulas, targets) if not f]
            if not updates:
                raise PortalError("Your salary cells contain formulas, so they can’t be updated here. "
                                  "Contact sales ops.")
            self.src.write(updates)
            months = m.table.month_labels
            self.src.audit(
                self.cfg.AUDIT_TAB,
                ["Timestamp", "Email", "Role", "Row"] + [f"Old {x}" for x in months] + [f"New {x}" for x in months],
                [now_str(), email, m.table.kind, m.row + 1] + before + vals,
            )
        finally:
            self.invalidate()
            self._lock.release()
