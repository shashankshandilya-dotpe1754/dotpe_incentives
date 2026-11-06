import os
import re
import sys

os.environ["DEMO_MODE"] = "1"
os.environ["COOKIE_SECURE"] = "0"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

import incentives as inc  # noqa: E402
from app import create_app  # noqa: E402
from config import Config  # noqa: E402
from sheets import DemoSource  # noqa: E402


@pytest.fixture
def client():
    app = create_app(Config, DemoSource())
    app.config["TESTING"] = True
    return app.test_client()


def login(c, email):
    c.post("/demo-login", data={"email": email})


def csrf(c):
    html = c.get("/").get_data(as_text=True)
    return re.search(r'data-csrf="([^"]+)"', html).group(1)


def test_pct_parsing():
    assert inc.to_pct(1) == 1
    assert inc.to_pct("100%") == 1
    assert inc.to_pct(75) == 0.75
    assert inc.to_pct("") is None


def test_tab_resolution_prefers_visible_and_current_quarter():
    tabs = [("Combined ACH (April, May, June'2026)", False),
            ("Combined ACH (July, August, September'2026)", False),
            ("Combined_ACH(AMJ25)", True)]
    got = inc.resolve_tab(tabs, Config.COMBINED_TAB_PATTERN, ["july", "august", "september"])
    assert got == "Combined ACH (July, August, September'2026)"
    assert inc.resolve_tab([("Quaterly Incentive(SMB Faming, Inbound, Enterprise", False)],
                           Config.MAIN_TAB_PATTERN)


def test_login_required(client):
    assert "Sign in" in client.get("/").get_data(as_text=True)


def test_unknown_email_denied(client):
    login(client, "someone.else@dotpe.in")
    r = client.get("/")
    assert r.status_code == 403


def test_bdm_sees_only_own_rows(client):
    login(client, "sharvan.kumar@dotpe.in")
    html = client.get("/").get_data(as_text=True)
    assert "₹26,809" in html or "₹26,810" in html  # total incl. Apr–Jun cases
    assert "The Crispy bites" in html and "GIANI ICE CREAM" in html
    # other people's merchants and incentives never appear
    assert "Sodhani Sweets" not in html and "MASSIVE RESTAURANTS" not in html
    assert "rajat.basak" not in html and "PRABHATI" not in html
    assert "₹122,241" not in html  # mayank's total


def test_grouping_100_and_below(client):
    login(client, "sharvan.kumar@dotpe.in")
    html = client.get("/").get_data(as_text=True)
    full = html.split('id="panel-full"')[1].split('id="panel-partial"')[0]
    part = html.split('id="panel-partial"')[1].split('remTitle')[0]
    assert "The Crispy bites" in full and "One Zero, coffee" in full       # 100% / QR n/a
    assert "THE THICK SHAKE" in part and "Gulf bites" in part             # live or QR < 100%
    assert "SP FOOD" in part                                              # blank live = not live
    rem = html.split("remTitle")[-1]
    assert "GIANI" in rem and "SUGUNA" in rem and "JIF" not in rem        # 100% excluded


def test_manager_gets_city_head_row(client):
    login(client, "nikhil.sandeep@dotpe.in")
    html = client.get("/").get_data(as_text=True)
    assert "(manager)" in html and "₹74,702" in html
    assert "Only for Salary Calculation" not in html


def test_save_salary_recalculates(client):
    login(client, "sharvan.kumar@dotpe.in")
    token = csrf(client)
    r = client.post("/api/salary", json={"salaries": ["10000", "10000", "10000"]},
                    headers={"X-CSRF-Token": token})
    assert r.status_code == 200, r.get_json()
    html = client.get("/?saved=1").get_data(as_text=True)
    # live EGM 117,620 - 30,000 = 87,620 x 12% = 10,514 (+12,695) = 23,209
    assert "₹23,209" in html and "Saved and recalculated." in html


def test_manager_salary_written_to_both_rows():
    src = DemoSource()
    app = create_app(Config, src)
    c = app.test_client()
    login(c, "nikhil.sandeep@dotpe.in")
    c.post("/api/salary", json={"salaries": [50000, 50000, 50000]}, headers={"X-CSRF-Token": csrf(c)})
    g = src.grids["Quaterly Incentive(SMB Faming, Inbound, Enterprise)"]
    tables = inc.find_tables(g)
    head = next(t for t in tables if t.kind == "HEAD")
    bdm_row = next(r for t in tables if t.kind == "BDM" for r in t.salary_only_rows
                   if "nikhil" in g.d(r, t.email_col))
    assert [g.raw[head.rows[0]][c] for c in head.salary_cols] == [50000, 50000, 50000]
    assert g.raw[bdm_row][2] == 50000
    assert len(src.audit_rows) == 1


def test_csrf_and_validation(client):
    login(client, "sharvan.kumar@dotpe.in")
    assert client.post("/api/salary", json={"salaries": [1, 2, 3]}).status_code == 400
    r = client.post("/api/salary", json={"salaries": ["-5", "0", "0"]},
                    headers={"X-CSRF-Token": csrf(client)})
    assert r.status_code == 400 and "zero or more" in r.get_json()["error"]
