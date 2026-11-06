"""
Data sources. The app only needs five operations, so swapping Google Sheets
for the demo source (or anything else) is easy.
"""
from __future__ import annotations

import re
from datetime import datetime

from incentives import Grid


class GoogleSheetSource:
    """Reads and writes the Google Sheet with a service account.
    Share the spreadsheet with the service account's email as an Editor."""

    def __init__(self, spreadsheet_id: str, service_account_file: str):
        import gspread
        self._gspread = gspread
        self.ss = gspread.service_account(filename=service_account_file).open_by_key(spreadsheet_id)

    @staticmethod
    def _quote(title: str) -> str:
        return "'" + title.replace("'", "''") + "'"

    def tabs(self) -> list[tuple[str, bool]]:
        meta = self.ss.fetch_sheet_metadata(params={"fields": "sheets.properties(title,hidden)"})
        return [(s["properties"]["title"], bool(s["properties"].get("hidden"))) for s in meta["sheets"]]

    def read(self, titles: list[str]) -> dict[str, Grid]:
        ranges = [self._quote(t) for t in titles]
        shown = self.ss.values_batch_get(ranges, params={"valueRenderOption": "FORMATTED_VALUE"})
        raw = self.ss.values_batch_get(ranges, params={"valueRenderOption": "UNFORMATTED_VALUE"})
        out = {}
        for t, d, r in zip(titles, shown.get("valueRanges", []), raw.get("valueRanges", [])):
            out[t] = Grid(t, d.get("values", []), r.get("values", []))
        return out

    def formulas(self, cells: list[str]) -> list[str]:
        if not cells:
            return []
        res = self.ss.values_batch_get(cells, params={"valueRenderOption": "FORMULA"})
        out = []
        for vr in res.get("valueRanges", []):
            v = (vr.get("values") or [[""]])[0]
            v = v[0] if v else ""
            out.append(v if isinstance(v, str) and v.startswith("=") else "")
        return out

    def write(self, updates: list[tuple[str, float]]) -> None:
        self.ss.values_batch_update({
            "valueInputOption": "RAW",
            "data": [{"range": a1, "values": [[v]]} for a1, v in updates],
        })

    def audit(self, tab: str, header: list, row: list) -> None:
        try:
            ws = self.ss.worksheet(tab)
        except self._gspread.WorksheetNotFound:
            ws = self.ss.add_worksheet(title=tab, rows=1000, cols=max(12, len(header)))
            ws.append_row(header)
        ws.append_row(row, value_input_option="USER_ENTERED")


# ---------------------------------------------------------------------------
# Demo source: an in-memory copy of the layout from the screenshots, so the
# app can be tried without any Google setup (DEMO_MODE=1).
# ---------------------------------------------------------------------------

def _parse_a1(a1: str) -> tuple[str, int, int]:
    m = re.match(r"^'((?:[^']|'')*)'!([A-Z]+)(\d+)$", a1)
    title, letters, num = m.group(1).replace("''", "'"), m.group(2), int(m.group(3))
    c = 0
    for ch in letters:
        c = c * 26 + ord(ch) - 64
    return title, num - 1, c - 1


class DemoSource:
    def __init__(self):
        from demo_data import build
        self.tab_list, self.grids, self.recalc = build()
        self.audit_rows: list = []

    def tabs(self):
        return list(self.tab_list)

    def read(self, titles):
        return {t: Grid(t, [list(r) for r in self.grids[t].display],
                        [list(r) for r in self.grids[t].raw]) for t in titles}

    def formulas(self, cells):
        return ["" for _ in cells]

    def write(self, updates):
        touched = set()
        for a1, v in updates:
            title, r, c = _parse_a1(a1)
            g = self.grids[title]
            g.raw[r][c] = v
            touched.add(title)
        for t in touched:
            self.recalc(self.grids[t])

    def audit(self, tab, header, row):
        self.audit_rows.append(row)


def make_source(cfg):
    if cfg.DEMO_MODE:
        return DemoSource()
    if not cfg.SPREADSHEET_ID:
        raise RuntimeError("Set SPREADSHEET_ID (the long id in the Google Sheet URL).")
    return GoogleSheetSource(cfg.SPREADSHEET_ID, cfg.SERVICE_ACCOUNT_FILE)


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
