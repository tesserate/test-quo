"""Daily snapshot job: pulls every contact + lead status, and the last 7
days of calls, and appends timestamped rows to the Google Sheet.

Run manually with `python ingest.py`, or on a schedule (see render.yaml).
"""
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

from config import CALLS_WINDOW_DAYS, EXCLUDED_SALESPERSON_USER_IDS, GOOGLE_CREDENTIALS_PATH, STATUS_ORDER
from quo.client import QuoClient
from quo.transform import (
    bucket_status,
    build_name_to_user_id,
    get_custom_field_values,
    get_owner_name,
    resolve_lead_status_key,
    resolve_owner_key,
)
from sheets import SheetStore

CALL_FETCH_WORKERS = 4

_thread_local = threading.local()


def _client_for_thread() -> QuoClient:
    # A requests.Session (and its SSL context) isn't safe to share across
    # threads, so each worker thread gets its own QuoClient/session.
    if not hasattr(_thread_local, "client"):
        _thread_local.client = QuoClient()
    return _thread_local.client


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_calls_for_contact(phone, phone_numbers, calls_after):
    client = _client_for_thread()
    rows = []
    for pn in phone_numbers:
        rows.extend(client.list_calls(pn["id"], phone, created_after=calls_after))
    return rows


def main():
    client = QuoClient()

    now = datetime.now(timezone.utc)
    snapshot_date = now.strftime("%Y-%m-%d")
    snapshot_at = iso(now)
    calls_after = iso(now - timedelta(days=CALLS_WINDOW_DAYS))

    custom_fields = client.list_custom_fields()
    lead_status_key = resolve_lead_status_key(custom_fields)
    owner_key = resolve_owner_key(custom_fields)
    if not lead_status_key:
        print(f"WARNING: no custom field named 'Lead Status' found. "
              f"Available fields: {[f.get('name') for f in custom_fields]}")
    if not owner_key:
        print(f"WARNING: no custom field named 'Owner' found. "
              f"Available fields: {[f.get('name') for f in custom_fields]}")

    name_to_user_id = build_name_to_user_id(client.list_users())

    contacts = client.list_contacts()
    print(f"Fetched {len(contacts)} contacts")

    phone_numbers = client.list_phone_numbers()
    if not phone_numbers:
        print("WARNING: no phone numbers found on this workspace, calls cannot be fetched.")

    contact_rows = []
    contacts_with_phone = []

    for contact in contacts:
        raw_status_values = get_custom_field_values(contact, lead_status_key) if lead_status_key else []
        status = bucket_status(raw_status_values, STATUS_ORDER)

        owner_name = get_owner_name(contact, owner_key)
        owner_user_id = name_to_user_id.get(owner_name.strip().lower()) if owner_name else None
        if owner_user_id in EXCLUDED_SALESPERSON_USER_IDS:
            owner_user_id = None

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
            owner_user_id or owner_name or "",
            contact.get("createdAt") or "",
        ])

        if phone and phone_numbers:
            contacts_with_phone.append((contact["id"], phone))

    print(f"Fetching last {CALLS_WINDOW_DAYS} days of calls for {len(contacts_with_phone)} "
          f"contacts across {len(phone_numbers)} phone numbers "
          f"({CALL_FETCH_WORKERS} workers)...")

    call_rows = []
    done = 0
    with ThreadPoolExecutor(max_workers=CALL_FETCH_WORKERS) as executor:
        futures = {
            executor.submit(fetch_calls_for_contact, phone, phone_numbers, calls_after): (contact_id, phone)
            for contact_id, phone in contacts_with_phone
        }
        for future in as_completed(futures):
            contact_id, phone = futures[future]
            for call in future.result():
                salesperson = call.get("userId")
                if salesperson in EXCLUDED_SALESPERSON_USER_IDS:
                    salesperson = None
                call_rows.append([
                    call["id"],
                    contact_id,
                    phone,
                    salesperson or "",
                    call.get("direction") or "",
                    call.get("duration") or 0,
                    call.get("createdAt") or "",
                    snapshot_at,
                ])
            done += 1
            if done % 200 == 0:
                print(f"  ...{done}/{len(contacts_with_phone)} contacts checked, {len(call_rows)} calls found so far")

    status_counts = {}
    for row in contact_rows:
        status_counts[row[6]] = status_counts.get(row[6], 0) + 1
    print(f"\nLead status breakdown (today): {status_counts}")

    minutes_by_salesperson = {}
    calls_by_salesperson = {}
    for row in call_rows:
        salesperson = row[3] or "(unassigned)"
        minutes_by_salesperson[salesperson] = minutes_by_salesperson.get(salesperson, 0) + row[5] / 60
        calls_by_salesperson[salesperson] = calls_by_salesperson.get(salesperson, 0) + 1
    print(f"Calls in the last {CALLS_WINDOW_DAYS} days by salesperson user id: {calls_by_salesperson}")
    print(f"Minutes in the last {CALLS_WINDOW_DAYS} days by salesperson user id: "
          f"{ {k: round(v, 1) for k, v in minutes_by_salesperson.items()} }")

    try:
        store = SheetStore()
    except FileNotFoundError:
        print(f"\nSkipped writing to Google Sheets: no credentials found at "
              f"{GOOGLE_CREDENTIALS_PATH}. Fetch/aggregation above still ran against the real "
              f"Quo data. Add a service account JSON (see README) and re-run to save.")
        return

    store.append_contacts_snapshot(contact_rows)
    new_calls = store.append_calls_snapshot(call_rows)
    print(f"\nSaved {len(contact_rows)} contact rows, {len(call_rows)} calls seen, {new_calls} new call rows saved to Google Sheets.")


if __name__ == "__main__":
    main()
