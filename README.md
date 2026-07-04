# test-quo

Pilot dashboard on top of the [Quo](https://www.quo.com) API: daily snapshot of
every contact's lead status and call activity, saved to a Google Sheet, viewed
through a small Streamlit dashboard.

## What it does

- `ingest.py` — run once a day. Pulls every contact + their `Lead Status`
  custom field, and every call from the last 7 days, and appends timestamped
  rows to two tabs in a Google Sheet (`Contacts Snapshot`, `Calls Snapshot`).
- `dashboard.py` — Streamlit app reading from that Sheet, showing:
  1. Contacts by lead status (today)
  2. Calls & minutes per salesperson, last 7 days
  3. How long contacts have sat in their current status (`<14` vs `>=14` days)
  4. Status changes vs. 7 days ago

## One important thing to verify before trusting the numbers

The Quo docs are inconsistent about where the "shared with" salesperson list
lives on a contact (webhook docs mention `sharedWithIds`; the REST
list-contacts schema doesn't show it). Before relying on the salesperson
attribution, run:

```
python probe.py
```

This prints one real contact, the custom field definitions, a phone number,
and a sample call. Confirm the real field name/location for the shared-users
list matches `quo/transform.py:get_shared_with_ids` — edit that function if
the real shape differs.

The business rule already encoded (per spec): a contact can be shared with
multiple users; `USusrXwEf3` is a shared/team id, not an individual
salesperson, so when there are multiple ids we skip it and attribute the
contact to whichever id comes right after it in the list. See
`config.EXCLUDED_SHARED_USER_ID` and `quo/transform.resolve_salesperson`.

## Local setup

1. Get a Quo API key: Quo → workspace settings → API tab → Generate API key
   (needs owner/admin access).
2. Create a Google service account so the scripts can write to your Sheet:
   - Go to https://console.cloud.google.com/ → create/select a project
   - Enable the **Google Sheets API** and **Google Drive API**
   - IAM & Admin → Service Accounts → Create service account
   - Create a JSON key for it and download it
   - Open the JSON, copy the `client_email` value
   - Open your sheet (https://docs.google.com/spreadsheets/d/1BXoxTXEGLJErGPsUX7GMtalw-IgiK1vQ0oeODiW6vy0/edit)
     → Share → paste that email in → give it **Editor** access
3. Clone and install:
   ```
   git clone git@github.com:tesserate/test-quo.git
   cd test-quo
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   ```
4. Fill in `.env`:
   - `QUO_API_KEY` — from step 1
   - `GOOGLE_CREDENTIALS_PATH` — path to the JSON key from step 2 (default:
     `google_credentials.json`, drop the file in the repo root — it's
     gitignored)
   - `GOOGLE_SHEET_ID` — already filled in with your sheet's id
5. Verify the API shape:
   ```
   python probe.py
   ```
6. Take a first snapshot:
   ```
   python ingest.py
   ```
   Run this daily for at least a week before the "status aging" and
   "week-over-week change" views become meaningful — they're both computed
   from snapshot history, not a single run.
7. View the dashboard:
   ```
   streamlit run dashboard.py
   ```

## Deploying (Render)

This repo includes `render.yaml` for a [Render Blueprint](https://render.com/docs/blueprint-spec):
one free web service running the dashboard, one free cron job running
`ingest.py` daily at 13:00 UTC (adjust the `schedule` in `render.yaml` for
your timezone).

1. Push this repo to GitHub (already set up if you're reading this from the repo).
2. In Render: New → Blueprint → pick this repo.
3. Render will create both services but the `sync: false` env vars need to be
   set manually per service (Render never wants secrets in the blueprint file
   itself):
   - `QUO_API_KEY`
   - `GOOGLE_SHEET_ID`
   - `GOOGLE_CREDENTIALS_JSON` — paste the **entire contents** of the service
     account JSON file as one value (not a file path — Render's free tier
     has no persistent disk, so the code reads credentials from this env var
     instead of `GOOGLE_CREDENTIALS_PATH` when it's set; see `sheets.py`).
4. Deploy. The dashboard URL is on the web service's page in Render.

## Tweaking things

Everything project-specific lives in `config.py`:
- `STATUS_ORDER` — the lead status labels shown as columns (anything else
  found in the data is folded into "Other")
- `EXCLUDED_SHARED_USER_ID` — the shared/team user id to skip
- `STATUS_AGING_THRESHOLD_DAYS` — the `<2 weeks` / `>=2 weeks` cutoff (days)
- `CALLS_WINDOW_DAYS` — the rolling window for the calls-per-salesperson view
