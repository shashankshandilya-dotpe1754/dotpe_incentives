"""Sample data in the same layout as the real sheet, used only when DEMO_MODE=1."""
from incentives import Grid, inr, find_tables, to_number

MAIN = "Quaterly Incentive(SMB Faming, Inbound, Enterprise)"
COMBINED = "Combined ACH (July, August, September'2026)"
COMBINED_OLD = "Combined ACH (April, May, June'2026)"
REMAINING = "Remaining ACH (April, May, June'2026)"

BDM_HEADERS = [
    "BDM", "July'2026 Salary", "August'2026 Salary", "September'2026 Salary", "Quarterly Salary",
    "Quarterly Leads", "Share of Mktg. cost per SPOC (quaterly)*", "Quaterly Gross Margin",
    "Rista Gross", "EGM (Excluding Refunds)", "LIVE_GM", "LIVE_EGM", "EGM Bucket", "Rista % to GM",
    "Rista% Bucket", "% Slab", "%Slab (Considering RISTA % in GM)", "Incentive Amount",
    "July'2026", "August'2026", "September'2026", "Refunds", "April, May, June LIVE GROSS Margin",
    "Incentive Amount April, May, June_Live Cases", "TOTAL Amount",
]  # columns B..Z
HEAD_HEADERS = [
    "EMP_ID", "Manager", "July'2026 Salary", "August'2026 Salary", "September'2026 Salary",
    "Quarterly Salary", "Quarterly Leads", "Share of Mktg. cost per SPOC (quaterly)*",
    "Quaterly Gross Margin", "Rista Gross", "EGM (Excluding Refunds)", "LIVE_GM", "LIVE_EGM",
    "EGM Bucket", "Rista % to GM", "Rista% Bucket", "% Slab", "%Slab (Considering RISTA % in GM)",
    "Incentive Amount", "Refunds", "April, May, June LIVE GROSS Margin",
    "Incentive Amount April, May, June_Live Cases", "TOTAL Amount",
]  # columns AC..AY

# email, gm, rista, liveGm, bucket, ristaBucket, slab, slabRista, refunds, prevGm, prevInc, manager
SMB = [
    ("parmeshwar.keshari@dotpe.in", 585134, 264531, 544253, ">250k", "-", .20, None, 0, 10000, 2000, "kushal.gupta@dotpe.in"),
    ("sugam.paswan@dotpe.in", 272330, 165668, 272330, ">250k", "-", .20, None, 0, 16000, 3200, "kushal.gupta@dotpe.in"),
    ("mausam.singh@dotpe.in", 461809, 151781, 429309, ">250k", "-", .20, None, 0, 17100, 3420, "parmeshwar.keshari@dotpe.in"),
]
INBOUND = [
    ("shivam.sharma@dotpe.in", 396078, 310285, 326278, ">250k", "-", .20, None, -6000, 62000, 12400, "kushal.gupta@dotpe.in"),
    ("bhupender.verma@dotpe.in", 412962, 287585, 350420, ">250k", "-", .20, None, -16000, 40500, 8100, "kushal.gupta@dotpe.in"),
]
ENTERPRISE = [
    ("sharvan.kumar@dotpe.in", 154953, 97500, 117620, "80k-160k", ">60%", .12, .12, 0, 105794, 12695, "nikhil.sandeep@dotpe.in"),
    ("mayank.chhillar@dotpe.in", 672204, 462986, 611204, ">250k", ">60%", .20, .20, 0, 0, 0, "ankur.mangla@dotpe.in"),
    ("arkaprava.chowdhury@dotpe.in", 500540, 184203, 184783, ">250k", "20%-40%", .12, .12, 0, 12000, 1440, "amit.shaw@dotpe.in"),
    ("rajat.basak@dotpe.in", 237822, 188102, 153853, "160k-250k", ">60%", .15, .15, -12000, -427, -64, "amit.shaw@dotpe.in"),
    ("ganesh.sonawane1@dotpe.in", 685937, 492695, 666166, ">250k", ">60%", .20, .20, -8400, 15000, 3000, "ganesh.sonawane1@dotpe.in"),
    ("shashikanth.charukula@dotpe.in", 84831, 63560, 31865, "80k-160k", ">60%", .12, .12, 0, 22150, 2658, "nikhil.sandeep@dotpe.in"),
]
SALARY_ONLY = [
    ("salman.khan@dotpe.in", 1029251, 723500, 775667),
    ("nikhil.sandeep@dotpe.in", 519076, 327093, 432593),
]
# email, emp id, gm, rista, liveGm, ristaBucket, slab, prevGm, prevInc
HEADS = [
    ("nikhil.sandeep@dotpe.in", "", 758861, 488153, 582078, ">60%", .10, 164944, 16494),
    ("salman.khan@dotpe.in", "935", 1029251, 723500, 775667, ">60%", .10, 63864, 6386),
]

ACH_HEADERS = ["Merchant Name", "POC", "Amount paid for", "Final Amount paid for", "Zoho DPAY ID",
               "Deal Ref ID", "Formula Invoice Value", "Gross Margin", "Live %", "QR Live %",
               "Live Gross Margin", "Rista Gross Margin"]
# merchant, poc, paid for, final, dpay, drf, invoice, live, qr (None = n/a), rista share
COMBINED_ROWS = [
    ("The Crispy bites", "sharvan.kumar@dotpe.in", "Rista Renewal", "Renewal-Subscription", "DPAY/33864", "DRF-A57659", 11800, 1, None, 1),
    ("One Zero, coffee", "sharvan.kumar@dotpe.in", "Rista Renewal", "Renewal-Subscription", "DPAY/33741", "DRF-A57486", 7000, 1, 1, 1),
    ("THE THICK SHAKE FACTORY PRIVATE LIMITED", "sharvan.kumar@dotpe.in", "Rista Premium", "New Outlet", "DPAY/33722", "DRF-A57450", 21240, 0.5, 1, 1),
    ("Gulf bites", "sharvan.kumar@dotpe.in", "QR Ordering Unified (Multi-Payment)", "Subscription-EM", "DPAY/34168", "DRF-A58016", 10000, 1, 0.67, 0),
    ("SP FOOD & BEVERAGES", "sharvan.kumar@dotpe.in", "Rista Renewal", "Renewal-Subscription", "DPAY/33836", "DRF-A57598", 7620, None, None, 1),
    ("Sodhani Sweets Private Limited", "rajat.basak@dotpe.in", "Rista Premium", "Subscription-NM", "DPAY/34012", "DRF-A57811", 59000, 1, 1, 1),
    ("Big Jaar", "rajat.basak@dotpe.in", "QR Ordering", "Subscription-NM", "DPAY/34055", "DRF-A57902", 23600, 0.75, 0.5, 0.4),
    ("MASSIVE RESTAURANTS PRIVATE LIMITED", "nikhil.sandeep@dotpe.in", "Subscription AR", "Subscription AR", "DPAY/34101", "DRF-A57950", 82600, 1, 1, 1),
]
# merchant, poc, paid for, final, dpay, drf, invoice, live, qr, rista share, difference
REMAINING_ROWS = [
    ("GIANI ICE CREAM PRIVATE LIMITED", "sharvan.kumar@dotpe.in", "Rista Premium", "Cross Sell", "DPAY/31646", "DRF-A54688", 14160, 0.5, 1, 1, 0.25),
    ("SUGUNA FOODS PRIVATE LIMITED", "sharvan.kumar@dotpe.in", "New Outlet AR", "Cross Sell", "DPAY/31702", "DRF-A54710", 28320, 0.75, 0.5, 1, 0.25),
    ("JIF (Mauritius) Private Limited", "sharvan.kumar@dotpe.in", "Rista Renewal", "Rista Renewal", "DPAY/31906", "DRF-A55068", 35400, 1, 1, 1, 0.5),
    ("PRABHATI FOODS PRIVATE LIMITED", "rajat.basak@dotpe.in", "Renewal-Subscription AR", "Rista Renewal", "DPAY/31544", "DRF-A54626", 21240, 0.6, None, 1, 0.1),
]


def _pct(v):
    return f"{v * 100:.0f}%"


class _Builder:
    def __init__(self, title, rows, cols):
        self.g = Grid(title, [[""] * cols for _ in range(rows)], [[""] * cols for _ in range(rows)])

    def put(self, r1, c0, raw, shown=None):
        self.g.raw[r1 - 1][c0] = raw
        self.g.display[r1 - 1][c0] = shown if shown is not None else str(raw)


def _main():
    b = _Builder(MAIN, 32, 52)
    B, AC = 1, 28

    def section(title_row, title, rows):
        b.put(title_row, B, title)
        for i, h in enumerate(BDM_HEADERS):
            b.put(title_row + 1, B + i, h)
        for n, row in enumerate(rows):
            r = title_row + 2 + n
            email, gm, rista, live, bucket, rb, slab, slabr, ref, pgm, pinc, mgr = row
            vals = [email, 0, 0, 0, 0, "", "", gm, rista, 0, live, 0, bucket, rista / gm, rb,
                    slab, slabr if slabr is not None else "-", 0, mgr, mgr, mgr, ref, pgm, pinc, 0]
            for i, v in enumerate(vals):
                b.put(r, B + i, v)
        return title_row + 2 + len(rows)

    section(1, "SMB_FARMING_BDM(July'2026, August'2026, September'2026)", SMB)
    section(8, "Inbound_BDM(July'2026, August'2026, September'2026)", INBOUND)
    end = section(15, "Enterprise_BDM(July'2026, August'2026, September'2026)", ENTERPRISE)
    for n, (email, gm, rista, live) in enumerate(SALARY_ONLY):
        r = end + n
        b.put(r, B, email)
        for i, v in enumerate([0, 0, 0, 0, "", "", gm, rista, 0, live, 0]):
            b.put(r, B + 1 + i, v)
        b.put(r, B + 12, "Only for Salary Calculation")

    b.put(15, AC, "Enterprise_City Heads (July'2026, August'2026, September'2026)")
    for i, h in enumerate(HEAD_HEADERS):
        b.put(16, AC + i, h)
    for n, (email, emp, gm, rista, live, rb, slab, pgm, pinc) in enumerate(HEADS):
        vals = [emp, email, 0, 0, 0, 0, "", "", gm, rista, 0, live, 0, "", rista / gm, rb, slab, "",
                0, 0, pgm, pinc, 0]
        for i, v in enumerate(vals):
            b.put(17 + n, AC + i, v)
    recalc(b.g)
    return b.g


def recalc(g: Grid):
    """Tiny stand-in for the sheet's formulas so saving a salary visibly changes the numbers."""
    for t in find_tables(g):
        f = t.fields
        for r in t.rows:
            sal = [to_number(g.raw[r][c]) or 0 for c in t.salary_cols]
            q = sum(sal)
            mk = to_number(g.raw[r][f["mktg"]]) or 0
            ref = to_number(g.raw[r][f["refunds"]]) or 0
            gm = to_number(g.raw[r][f["gm"]]) or 0
            live = to_number(g.raw[r][f["liveGm"]]) or 0
            egm, legm = gm - q - mk + ref, live - q - mk + ref
            vals = {"salaryQ": q, "egm": egm, "liveEgm": legm}
            if r not in t.salary_only_rows:
                slab_c = f["slabRista"] if to_number(g.raw[r][f["slabRista"]]) is not None else f["slab"]
                slab = to_number(g.raw[r][slab_c]) or 0
                inc = round(legm * slab)
                vals.update(incentive=inc, total=inc + (to_number(g.raw[r][f["prevIncentive"]]) or 0))
            for k, v in vals.items():
                g.raw[r][f[k]] = v
            for c in range(t.first_col, t.last_col + 1):
                v = g.raw[r][c]
                if c == f.get("ristaPct") and isinstance(v, float):
                    g.display[r][c] = _pct(v)
                elif c in (f.get("slab"), f.get("slabRista")) and isinstance(v, float):
                    g.display[r][c] = _pct(v)
                elif isinstance(v, (int, float)) and not isinstance(v, bool) and c != t.email_col:
                    g.display[r][c] = inr(v)
                else:
                    g.display[r][c] = str(v)


def _ach(title, headers, rows, remaining=False):
    b = _Builder(title, len(rows) + 1, len(headers))
    for i, h in enumerate(headers):
        b.put(1, i, h)
    for n, row in enumerate(rows):
        merchant, poc, paid, final, dpay, drf, inv, live, qr, rshare = row[:10]
        gm = inv / 1.18
        lgm = gm * (live or 0)
        vals = [merchant, poc, paid, final, dpay, drf, (inv, inr(inv)), (gm, inr(gm)),
                (live if live is not None else "", _pct(live) if live is not None else ""),
                (qr if qr is not None else "", _pct(qr) if qr is not None else ""),
                (lgm, inr(lgm)), (gm * rshare, inr(gm * rshare))]
        if remaining:
            diff = row[10]
            vals += [(diff, _pct(diff)), (gm * min(1, (live or 0) + diff), inr(gm * min(1, (live or 0) + diff)))]
        for i, v in enumerate(vals):
            raw, shown = v if isinstance(v, tuple) else (v, v)
            b.put(n + 2, i, raw, shown)
    return b.g


def build():
    grids = {
        MAIN: _main(),
        COMBINED: _ach(COMBINED, ACH_HEADERS, COMBINED_ROWS),
        COMBINED_OLD: _ach(COMBINED_OLD, ACH_HEADERS, []),
        REMAINING: _ach(REMAINING, ACH_HEADERS + ["Difference %", "New Live Gross Margin"],
                        REMAINING_ROWS, remaining=True),
    }
    tabs = [(MAIN, False), ("Sheet28", False), (COMBINED, False), (REMAINING, False),
            (COMBINED_OLD, True), ("Mapping(SMB Farming, Inbound, Enterprise)", False),
            ("Refund", False), ("Marketing Cost", False), ("LIVE/NOT_LIVE", False)]
    return tabs, grids, recalc
