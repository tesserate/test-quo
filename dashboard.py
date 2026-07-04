"""Simple Streamlit dashboard reading snapshots saved by ingest.py.

Run with: streamlit run dashboard.py
"""
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from config import (
    CALLS_HEADER,
    CALLS_TAB,
    CONTACTS_HEADER,
    CONTACTS_TAB,
    STATUS_AGING_THRESHOLD_DAYS,
    STATUS_ORDER,
)
from quo.client import QuoClient
from sheets import SheetStore

st.set_page_config(page_title="Quo Pilot Dashboard", layout="wide")


@st.cache_data(ttl=300)
def load_data():
    store = SheetStore()
    contacts_df = store.read_df(CONTACTS_TAB, CONTACTS_HEADER)
    calls_df = store.read_df(CALLS_TAB, CALLS_HEADER)
    return contacts_df, calls_df


@st.cache_data(ttl=3600)
def load_user_names():
    try:
        users = QuoClient().list_users()
    except Exception:
        return {}
    names = {}
    for u in users:
        name = f"{u.get('firstName') or ''} {u.get('lastName') or ''}".strip()
        names[u["id"]] = name or u.get("email") or u["id"]
    return names


def name_for(user_id: str, names: dict) -> str:
    if not user_id:
        return "(unassigned)"
    return names.get(user_id, user_id)


st.title("Quo Pilot Dashboard")

if st.button("Refresh data"):
    st.cache_data.clear()

contacts_df, calls_df = load_data()
user_names = load_user_names()

if contacts_df.empty:
    st.warning("No contact snapshots yet. Run `python ingest.py` at least once.")
    st.stop()

contacts_df["snapshot_date"] = pd.to_datetime(contacts_df["snapshot_date"])
latest_date = contacts_df["snapshot_date"].max()
latest_df = contacts_df[contacts_df["snapshot_date"] == latest_date]

st.caption(f"Latest snapshot: {latest_date.date()}")

st.header("1. Contacts by Lead Status")
status_counts = latest_df["lead_status"].value_counts()
status_counts = status_counts.reindex(STATUS_ORDER, fill_value=0)
status_counts.index.name = "status"
st.bar_chart(status_counts)
st.dataframe(status_counts.rename("count").reset_index(), hide_index=True)

st.header(f"2. Calls & minutes per salesperson (last 7 days)")
if calls_df.empty:
    st.info("No call snapshots yet.")
else:
    calls_df["duration_sec"] = pd.to_numeric(calls_df["duration_sec"], errors="coerce").fillna(0)
    calls_df["created_at"] = pd.to_datetime(calls_df["created_at"], errors="coerce", utc=True)
    window_start = pd.Timestamp.now(tz="UTC") - timedelta(days=7)
    recent_calls = calls_df[calls_df["created_at"] >= window_start]
    per_sales = recent_calls.groupby("salesperson_user_id").agg(
        calls=("call_id", "count"),
        minutes=("duration_sec", lambda s: round(s.sum() / 60, 1)),
    ).reset_index()
    per_sales["salesperson"] = per_sales["salesperson_user_id"].apply(lambda u: name_for(u, user_names))
    st.dataframe(per_sales[["salesperson", "calls", "minutes"]], hide_index=True)

st.header("3. Time in current status")


def compute_status_age(contacts_df: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    rows = []
    for contact_id, group in contacts_df.groupby("contact_id"):
        group = group.sort_values("snapshot_date")
        current_status = group.iloc[-1]["lead_status"]
        # Walk backward from the latest snapshot to find when this contact
        # last entered its current status.
        since_date = group.iloc[-1]["snapshot_date"]
        for _, row in group[::-1].iterrows():
            if row["lead_status"] != current_status:
                break
            since_date = row["snapshot_date"]
        days_in_status = (as_of - since_date).days
        rows.append({"contact_id": contact_id, "status": current_status, "days_in_status": days_in_status})
    return pd.DataFrame(rows)


age_df = compute_status_age(contacts_df, latest_date)
if not age_df.empty:
    age_df["bucket"] = age_df["days_in_status"].apply(
        lambda d: f"< {STATUS_AGING_THRESHOLD_DAYS} days" if d < STATUS_AGING_THRESHOLD_DAYS else f">= {STATUS_AGING_THRESHOLD_DAYS} days"
    )
    pivot = age_df.pivot_table(index="status", columns="bucket", values="contact_id", aggfunc="count", fill_value=0)
    pivot = pivot.reindex(STATUS_ORDER, fill_value=0)
    st.dataframe(pivot)

st.header("4. Status changes vs. last week")

target_date = latest_date - timedelta(days=7)
prior_dates = contacts_df.loc[contacts_df["snapshot_date"] <= target_date, "snapshot_date"]
if prior_dates.empty:
    st.info("Not enough history yet — need at least 7 days of daily snapshots.")
else:
    prior_date = prior_dates.max()
    prior_df = contacts_df[contacts_df["snapshot_date"] == prior_date].set_index("contact_id")["lead_status"]
    current_df = latest_df.set_index("contact_id")["lead_status"]
    merged = pd.concat([prior_df.rename("old_status"), current_df.rename("new_status")], axis=1).dropna()
    changed = merged[merged["old_status"] != merged["new_status"]]
    st.caption(f"Comparing {prior_date.date()} -> {latest_date.date()}")
    col1, col2 = st.columns(2)
    col1.metric("Contacts changed status", len(changed))
    col2.metric("Contacts unchanged", len(merged) - len(changed))
    if not changed.empty:
        display = changed.reset_index().merge(
            latest_df[["contact_id", "first_name", "last_name"]], on="contact_id", how="left"
        )
        display["name"] = (display["first_name"].fillna("") + " " + display["last_name"].fillna("")).str.strip()
        st.dataframe(display[["name", "old_status", "new_status"]], hide_index=True)
