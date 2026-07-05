from __future__ import annotations

import requests

from config import QUO_API_KEY, QUO_BASE_URL


class QuoClient:
    def __init__(self, api_key: str = QUO_API_KEY, base_url: str = QUO_BASE_URL):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": api_key,
            "Accept": "application/json",
        })
        self.base_url = base_url

    def _get(self, path: str, params: dict | None = None) -> dict:
        resp = self.session.get(f"{self.base_url}{path}", params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _paginated(self, path: str, params: dict) -> list[dict]:
        items: list[dict] = []
        page_token = None
        while True:
            page_params = dict(params)
            if page_token:
                page_params["pageToken"] = page_token
            body = self._get(path, page_params)
            items.extend(body.get("data", []))
            page_token = body.get("nextPageToken")
            if not page_token:
                return items

    def list_contacts(self) -> list[dict]:
        return self._paginated("/v1/contacts", {"maxResults": 50})

    def list_custom_fields(self) -> list[dict]:
        return self._get("/v1/contact-custom-fields").get("data", [])

    def list_phone_numbers(self) -> list[dict]:
        return self._get("/v1/phone-numbers").get("data", [])

    def list_users(self) -> list[dict]:
        return self._paginated("/v1/users", {"maxResults": 50})

    def list_calls(self, phone_number_id: str, participant: str,
                   created_after: str | None = None,
                   created_before: str | None = None) -> list[dict]:
        params = {"phoneNumberId": phone_number_id, "participants": [participant], "maxResults": 100}
        if created_after:
            params["createdAfter"] = created_after
        if created_before:
            params["createdBefore"] = created_before
        return self._paginated("/v1/calls", params)
