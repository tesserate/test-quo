from __future__ import annotations

import re

from config import LEAD_STATUS_FIELD_NAME, OWNER_FIELD_NAME


def resolve_custom_field_key(custom_fields: list[dict], field_name: str) -> str | None:
    for field in custom_fields:
        if field.get("name", "").strip().lower() == field_name.lower():
            return field.get("key")
    return None


def resolve_lead_status_key(custom_fields: list[dict]) -> str | None:
    return resolve_custom_field_key(custom_fields, LEAD_STATUS_FIELD_NAME)


def resolve_owner_key(custom_fields: list[dict]) -> str | None:
    return resolve_custom_field_key(custom_fields, OWNER_FIELD_NAME)


def get_custom_field_values(contact: dict, field_key: str) -> list[str]:
    """Multi-select custom fields return a list of selected option strings.
    Some historical records have stray bracket characters from a bad import
    (e.g. "[Submitted form]") -- strip those."""
    for field in contact.get("customFields", []):
        if field.get("key") != field_key:
            continue
        value = field.get("value")
        if value is None:
            return []
        if not isinstance(value, list):
            value = [value]
        return [v.strip("[]").strip() for v in value if v]
    return []


def _normalize(label: str) -> str:
    return re.sub(r"\s+", " ", label).strip().lower().rstrip("s")


def bucket_status(raw_values: list[str], status_order: list[str]) -> str:
    """Lead Status is multi-select, so a contact can hold more than one value
    at once (e.g. "Submitted form" and "Large Build Form" together). Use the
    furthest-along recognized stage in status_order; anything unrecognized,
    including no value at all, falls into "Other"."""
    normalized = {_normalize(v) for v in raw_values}
    for status in status_order:
        if status == "Other":
            continue
        if _normalize(status) in normalized:
            return status
    return "Other"


def get_owner_name(contact: dict, owner_field_key: str | None) -> str | None:
    if not owner_field_key:
        return None
    values = get_custom_field_values(contact, owner_field_key)
    return values[0] if values else None


def build_name_to_user_id(users: list[dict]) -> dict[str, str]:
    return {u["firstName"].strip().lower(): u["id"] for u in users if u.get("firstName")}
