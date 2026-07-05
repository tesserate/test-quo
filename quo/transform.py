from __future__ import annotations

from config import EXCLUDED_SHARED_USER_ID, LEAD_STATUS_FIELD_NAME


def resolve_lead_status_key(custom_fields: list[dict]) -> str | None:
    for field in custom_fields:
        if field.get("name", "").strip().lower() == LEAD_STATUS_FIELD_NAME.lower():
            return field.get("key")
    return None


def get_custom_field_value(contact: dict, field_key: str) -> str | None:
    for field in contact.get("customFields", []):
        if field.get("key") != field_key:
            continue
        if field.get("value") is not None:
            return field["value"]
        values = field.get("values")
        if values:
            return values[0]
    return None


def get_shared_with_ids(contact: dict) -> list[str]:
    """Contacts have both a single-owner `userId` field and a `sharedWith`
    array of user ids. Salesperson attribution uses sharedWith, not userId."""
    return contact.get("sharedWith") or []


def resolve_salesperson(shared_with_ids: list[str]) -> str | None:
    """USusrXwEf3 is a shared/team id, not an individual salesperson. When
    multiple ids are present, skip it and use the id that follows it."""
    ids = [i for i in shared_with_ids if i]
    if not ids:
        return None
    if len(ids) == 1:
        return ids[0]
    if EXCLUDED_SHARED_USER_ID in ids:
        idx = ids.index(EXCLUDED_SHARED_USER_ID)
        if idx + 1 < len(ids):
            return ids[idx + 1]
        remaining = [i for i in ids if i != EXCLUDED_SHARED_USER_ID]
        if remaining:
            return remaining[0]
    return ids[0]


def bucket_status(raw_status: str | None, status_order: list[str]) -> str:
    if raw_status in status_order:
        return raw_status
    return "Other"
