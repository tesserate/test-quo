import os

from dotenv import load_dotenv

load_dotenv()

QUO_API_KEY = os.environ["QUO_API_KEY"]
QUO_BASE_URL = "https://api.quo.com"

GOOGLE_CREDENTIALS_PATH = os.environ.get("GOOGLE_CREDENTIALS_PATH", "google_credentials.json")
# On Render, paste the full service-account JSON into this env var instead of
# uploading a file. Local dev can just use GOOGLE_CREDENTIALS_PATH.
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON")
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]

CONTACTS_TAB = "Contacts Snapshot"
CALLS_TAB = "Calls Snapshot"

CONTACTS_HEADER = [
    "snapshot_date", "snapshot_at", "contact_id", "first_name", "last_name",
    "phone", "lead_status", "owner_user_id", "contact_created_at",
]
CALLS_HEADER = [
    "call_id", "contact_id", "phone", "salesperson_user_id",
    "direction", "duration_sec", "created_at", "saved_at",
]

# Names of the custom fields to read, resolved dynamically against
# /v1/contact-custom-fields by name (case-insensitive) rather than a hardcoded
# key, since custom field keys are workspace-specific opaque ids.
LEAD_STATUS_FIELD_NAME = "Lead Status"
OWNER_FIELD_NAME = "Owner"

# Order to display lead status columns in; anything not matching one of these
# (case/pluralization-insensitively) is folded into "Other". Confirmed via
# probe.py that Lead Status is multi-select and real workspace data is messier
# than this list (also has Dropped, Large Build Form, circle back, Promising,
# Closed, Called) -- those all fall into Other.
STATUS_ORDER = [
    "Submitted form",
    "Quoting call Booked",
    "Quoted",
    "Closing Call",
    "Other",
]

# The workspace owner isn't an individual salesperson -- excluded from
# salesperson-level call/ownership stats.
EXCLUDED_SALESPERSON_USER_IDS = {"USusrXwEf3"}

STATUS_AGING_THRESHOLD_DAYS = 14
CALLS_WINDOW_DAYS = 7
