"""Daily snapshot job: pulls every contact + lead status, and the last 7
days of calls, and appends timestamped rows to the Google Sheet.

Run manually with `python ingest.py`, or on a schedule (see render.yaml).
"""
from datetime import datetime, timedelta, timezone

from config import CALLS_WINDOW_DAYS, STATUS_ORDER
from quo.client import QuoClient
from quo.transform import (
    bucket_status,
    get_custom_field_value,
    get_shared_with_ids,
    resolve_lead_status_key,
    resolve_salesperson,
)
from sheets import SheetStore


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    client = QuoClient()
    store = SheetStore()

    now = datetime.now(timezone.utc)
    snapshot_date = now.strftime("%Y-%m-%d")
    snapshot_at = iso(now)
    calls_after = iso(now - timedelta(days=CALLS_WINDOW_DAYS))

    custom_fields = client.list_custom_fields()
    lead_status_key = resolve_lead_status_key(custom_fields)
    if not lead_status_key:
        print(f"WARNING: no custom field named 'Lead Status' found. "
              f"Available fields: {[f.get('name') for f in custom_fields]}")

    contacts = client.list_contacts()
    print(f"Fetched {len(contacts)} contacts")

    phone_numbers = client.list_phone_numbers()
    if not phone_numbers:
        print("WARNING: no phone numbers found on this workspace, calls cannot be fetched.")

    contact_rows = []
    call_rows = []

    for contact in contacts:
        shared_with = get_shared_with_ids(contact)
        salesperson = resolve_salesperson(shared_with)
        raw_status = get_custom_field_value(contact, lead_status_key) if lead_status_key else None
        status = bucket_status(raw_status, STATUS_ORDER)

        default_fields = contact.get("defaultFields", {})
        phones = default_fields.get("phoneNumbers", []) or []
        phone = phones[0]["value"] if phones and phones[0].get("value") else None

        contact_rows.append([
            snapshot_date,
            snapshot_at,
            contact["id"],
            default_fields.get("firstName") or "",
            default_fields.get("lastName") or "",
            phone or "",
            status,
            salesperson or "",
            contact.get("createdAt") or "",
        ])

        if not phone:
            continue

        for pn in phone_numbers:
            calls = client.list_calls(pn["id"], phone, created_after=calls_after)
            for call in calls:
                call_rows.append([
                    call["id"],
                    contact["id"],
                    phone,
                    salesperson or "",
                    call.get("direction") or "",
                    call.get("duration") or 0,
                    call.get("createdAt") or "",
                    snapshot_at,
                ])

    store.append_contacts_snapshot(contact_rows)
    new_calls = store.append_calls_snapshot(call_rows)
    print(f"Saved {len(contact_rows)} contact rows, {len(call_rows)} calls seen, {new_calls} new call rows saved.")


if __name__ == "__main__":
    main()
