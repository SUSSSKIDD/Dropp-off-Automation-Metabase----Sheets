import os
import requests
import pandas as pd
from datetime import datetime
import pytz

METABASE_URL = os.environ["METABASE_URL"].rstrip("/")
METABASE_EMAIL = os.environ["METABASE_EMAIL"]
METABASE_PASSWORD = os.environ["METABASE_PASSWORD"]
METABASE_QUESTION_ID = int(os.environ.get("METABASE_QUESTION_ID", "33548"))

DATETIME_COLS = [
    "Form Filled At IST",
    "Latest Completed AI Call Started At IST",
    "Meeting Booked At IST",
]

_session_token: str | None = None


def _get_session_token() -> str:
    global _session_token
    if _session_token:
        return _session_token
    resp = requests.post(
        f"{METABASE_URL}/api/session",
        json={"username": METABASE_EMAIL, "password": METABASE_PASSWORD},
        timeout=30,
    )
    resp.raise_for_status()
    _session_token = resp.json()["id"]
    return _session_token


def _fetch(start_date: str, end_date: str) -> pd.DataFrame:
    global _session_token
    token = _get_session_token()
    url = f"{METABASE_URL}/api/card/{METABASE_QUESTION_ID}/query/json"
    headers = {"X-Metabase-Session": token, "Content-Type": "application/json"}
    payload = {
        "parameters": [
            {"type": "date/single", "target": ["variable", ["template-tag", "lead_start_date"]], "value": start_date},
            {"type": "date/single", "target": ["variable", ["template-tag", "lead_end_date"]], "value": end_date},
        ]
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=60)
    if resp.status_code == 401:
        _session_token = None
        headers["X-Metabase-Session"] = _get_session_token()
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()

    df = pd.DataFrame(resp.json())
    if df.empty:
        return df
    df.columns = [c.strip() for c in df.columns]
    df = df.copy()
    for col in DATETIME_COLS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def fetch_leads() -> pd.DataFrame:
    global _session_token
    ist = pytz.timezone("Asia/Kolkata")
    today = datetime.now(ist).strftime("%Y-%m-%d")

    return _fetch(today, today)


def fetch_leads_range(start_date: str, end_date: str) -> pd.DataFrame:
    return _fetch(start_date, end_date)
