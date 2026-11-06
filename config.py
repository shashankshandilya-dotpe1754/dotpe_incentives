import os

try:  # load settings from a .env file if python-dotenv is installed
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _bool(name: str, default: bool) -> bool:
    return os.environ.get(name, "1" if default else "0").strip().lower() in ("1", "true", "yes", "on")


class Config:
    # Flask session signing key: long random string, keep secret.
    SECRET_KEY = os.environ.get("SECRET_KEY", "")

    # Google Sheet: the long id between /d/ and /edit in the sheet URL.
    SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "")
    SERVICE_ACCOUNT_FILE = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "service-account.json")

    # Google sign-in (OAuth client of type "Web application").
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    ALLOWED_DOMAIN = os.environ.get("ALLOWED_DOMAIN", "dotpe.in").lower()

    # Tab names change every quarter, so tabs are matched by pattern, not exact name.
    # Visible tabs win over hidden ones; for Combined ACH, the tab naming the current
    # quarter's months wins. Set an exact *_TAB_NAME to override.
    MAIN_TAB_PATTERN = os.environ.get("MAIN_TAB_PATTERN", r"^qua(r)?terly\s*incentive")
    COMBINED_TAB_PATTERN = os.environ.get("COMBINED_TAB_PATTERN", r"^combined\s*ach")
    REMAINING_TAB_PATTERN = os.environ.get("REMAINING_TAB_PATTERN", r"^remaining\s*ach")
    MAIN_TAB_NAME = os.environ.get("MAIN_TAB_NAME", "")
    COMBINED_TAB_NAME = os.environ.get("COMBINED_TAB_NAME", "")
    REMAINING_TAB_NAME = os.environ.get("REMAINING_TAB_NAME", "")

    EDITS_OPEN = _bool("EDITS_OPEN", True)            # set to 0 after the salary deadline
    MAX_MONTHLY_SALARY = float(os.environ.get("MAX_MONTHLY_SALARY", "1000000"))
    AUDIT_TAB = os.environ.get("AUDIT_TAB", "Salary Audit Log")
    CACHE_SECONDS = int(os.environ.get("CACHE_SECONDS", "60"))

    COOKIE_SECURE = _bool("COOKIE_SECURE", True)       # needs HTTPS; set 0 for local testing
    DEMO_MODE = _bool("DEMO_MODE", False)              # sample data + test sign-in, no Google needed
