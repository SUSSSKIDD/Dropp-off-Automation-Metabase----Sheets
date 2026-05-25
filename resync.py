"""
One-time resync: backfills the no-meeting sheet from a given start date.
Checks: Lead Type = QL, Call Completion = True, Meeting Booked At IST = blank.
No Telegram alerts sent — sheet only.

Usage:
    python resync.py                  # defaults to 2026-05-23 → today
    python resync.py 2026-05-23       # explicit start date
"""
from dotenv import load_dotenv
load_dotenv()

import sys
import pytz
from datetime import datetime
from metabase import fetch_leads_range
from sheets import append_no_meeting, get_no_meeting_ids
import pandas as pd
from datetime import timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

def _is_empty(val) -> bool:
    if val is None:
        return True
    try:
        return bool(pd.isna(val))
    except Exception:
        return False

def _to_utc(dt):
    try:
        if dt is None or _is_empty(dt):
            return None
        if hasattr(dt, 'tzinfo') and dt.tzinfo is None:
            return dt.replace(tzinfo=IST).astimezone(timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

def resync(start_date: str):
    ist = pytz.timezone("Asia/Kolkata")
    end_date = datetime.now(ist).strftime("%Y-%m-%d")

    print(f"Fetching leads from {start_date} to {end_date}...")
    df = fetch_leads_range(start_date, end_date)
    print(f"Total leads fetched: {len(df)}")

    existing_ids = get_no_meeting_ids()
    print(f"Already in sheet: {len(existing_ids)} entries")

    ql = df[df["Lead Type"].str.strip().str.upper() == "QL"]
    print(f"QL leads: {len(ql)}")

    written = 0
    skipped_dedup = 0
    skipped_no_qualify = 0

    for _, row in ql.iterrows():
        uid = str(row.get("Pre User ID", "")).strip()
        if not uid or uid == "nan":
            continue

        if uid in existing_ids:
            skipped_dedup += 1
            continue

        call_completed = row.get("Call Completion")
        call_is_true = bool(call_completed) if call_completed not in (None, "", "nan") and not _is_empty(call_completed) else False
        call_time = _to_utc(row.get("Latest Completed AI Call Started At IST"))
        meeting_empty = _is_empty(row.get("Meeting Booked At IST"))

        if call_is_true and call_time is not None and meeting_empty:
            entry = row.to_dict()
            append_no_meeting(entry)
            existing_ids.add(uid)
            written += 1
            print(f"  ✓ Added: {uid} — {row.get('Name')} (call at {row.get('Latest Completed AI Call Started At IST')})")
        else:
            skipped_no_qualify += 1

    print(f"\nDone. Written: {written} | Skipped (already in sheet): {skipped_dedup} | Not qualifying: {skipped_no_qualify}")

if __name__ == "__main__":
    start = sys.argv[1] if len(sys.argv) > 1 else "2026-05-23"
    resync(start)
