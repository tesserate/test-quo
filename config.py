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
    "phone", "lead_status", "salesperson_user_id", "contact_created_at",
]
CALLS_HEADER = [
    "call_id", "contact_id", "phone", "salesperson_user_id",
    "direction", "duration_sec", "created_at", "saved_at",
]

# The name of the custom field to read for pipeline stage, resolved dynamically
# against /v1/contact-custom-fields by name (case-insensitive) rather than a
# hardcoded key, since custom field keys can change per-workspace.
LEAD_STATUS_FIELD_NAME = "Lead Status"

# Order to display lead status columns in; anything not in this list is folded
# into "Other".
STATUS_ORDER = [
    "Submitted form",
    "Quoting call Booked",
    "Quoted",
    "Closing Call",
    "Other",
]

# Contacts can be shared with multiple workspace users. USusrXwEf3 is a shared
# team-level id rather than an individual salesperson, so when a contact has
# multiple sharedWith ids we skip it and attribute the contact to the id that
# follows it in the list. Confirmed via probe.py against real data.
EXCLUDED_SHARED_USER_ID = "USusrXwEf3"

STATUS_AGING_THRESHOLD_DAYS = 14
CALLS_WINDOW_DAYS = 7
