"""Run this once against your real Quo account before trusting ingest.py.

It prints one raw contact, the custom field definitions, one phone number,
and (if possible) one call, so we can confirm the actual field names Quo
returns -- in particular where the "shared with" salesperson list actually
lives on a contact, since the public docs are inconsistent about it (webhook
docs mention `sharedWithIds`, the REST list-contacts schema doesn't show it
at all).

Usage: python probe.py
"""
import json

from quo.client import QuoClient


def main():
    client = QuoClient()

    print("=== Custom field definitions (/v1/contact-custom-fields) ===")
    fields = client.list_custom_fields()
    print(json.dumps(fields, indent=2))

    print("\n=== First contact (/v1/contacts) ===")
    contacts = client.list_contacts()
    print(f"Total contacts fetched: {len(contacts)}")
    if contacts:
        print(json.dumps(contacts[0], indent=2))
    else:
        print("No contacts found.")

    print("\n=== Phone numbers (/v1/phone-numbers) ===")
    phone_numbers = client.list_phone_numbers()
    print(json.dumps(phone_numbers, indent=2))

    if contacts and phone_numbers:
        contact_phones = contacts[0].get("defaultFields", {}).get("phoneNumbers", [])
        if contact_phones:
            phone = contact_phones[0]["value"]
            phone_number_id = phone_numbers[0]["id"]
            print(f"\n=== Sample calls for participant={phone} phoneNumberId={phone_number_id} ===")
            calls = client.list_calls(phone_number_id, phone)
            print(json.dumps(calls[:3], indent=2))
        else:
            print("\nFirst contact has no phone number on file, skipping call sample.")

    print(
        "\nCheck above: does the contact object contain 'sharedWithIds' or "
        "'sharedWith'? Update quo/transform.py:get_shared_with_ids if the "
        "real field name/location differs."
    )


if __name__ == "__main__":
    main()
