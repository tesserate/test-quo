import json

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

from config import (
    CALLS_HEADER,
    CALLS_TAB,
    CONTACTS_HEADER,
    CONTACTS_TAB,
    GOOGLE_CREDENTIALS_JSON,
    GOOGLE_CREDENTIALS_PATH,
    GOOGLE_SHEET_ID,
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


class SheetStore:
    def __init__(self):
        if GOOGLE_CREDENTIALS_JSON:
            info = json.loads(GOOGLE_CREDENTIALS_JSON)
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        else:
            creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_PATH, scopes=SCOPES)
        self.gc = gspread.authorize(creds)
        self.sh = self.gc.open_by_key(GOOGLE_SHEET_ID)

    def _get_or_create_tab(self, name: str, header: list[str]):
        try:
            return self.sh.worksheet(name)
        except gspread.WorksheetNotFound:
            ws = self.sh.add_worksheet(title=name, rows=1000, cols=len(header))
            ws.append_row(header)
            return ws

    def append_contacts_snapshot(self, rows: list[list]) -> None:
        if not rows:
            return
        ws = self._get_or_create_tab(CONTACTS_TAB, CONTACTS_HEADER)
        ws.append_rows(rows, value_input_option="RAW")

    def append_calls_snapshot(self, rows: list[list]) -> int:
        """Rows are keyed by call_id (first column). Since the same call can
        fall inside the rolling 7-day window on multiple daily runs, skip any
        call_id already present so the tab stays append-only without dupes.
        """
        if not rows:
            return 0
        ws = self._get_or_create_tab(CALLS_TAB, CALLS_HEADER)
        existing_ids = set(ws.col_values(1)[1:])
        new_rows = [r for r in rows if r[0] not in existing_ids]
        if new_rows:
            ws.append_rows(new_rows, value_input_option="RAW")
        return len(new_rows)

    def read_df(self, tab_name: str, header: list[str]) -> pd.DataFrame:
        ws = self._get_or_create_tab(tab_name, header)
        records = ws.get_all_records()
        return pd.DataFrame.from_records(records, columns=header) if records else pd.DataFrame(columns=header)
