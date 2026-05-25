"""
One-time resync: backfills no-call and no-meeting sheets from a given start date.
No Telegram alerts sent — sheet writes only.

Usage:
    python resync.py                  # defaults to 2026-05-22 → today
    python resync.py 2026-05-22       # explicit start date
"""
from dotenv import load_dotenv
load_dotenv()

import sys
import pytz
import pandas as pd
from datetime import datetime, timezone, timedelta
from metabase import fetch_leads_range
from sheets import append_no_call, get_no_call_ids, append_no_meeting, get_no_meeting_ids

IST = timezone(timedelta(hours=5, minutes=30))


def _is_null(val) -> bool:
    if val is None:
        return True
    try:
        return bool(pd.isna(val))
    except Exception:
        return False


def _to_utc(dt):
    try:
        if dt is None or _is_null(dt):
            return None
        if hasattr(dt, 'tzinfo') and dt.tzinfo is None:
            return dt.replace(tzinfo=IST).astimezone(timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def resync(start_date: str):
    ist_tz = pytz.timezone("Asia/Kolkata")
    end_date = datetime.now(ist_tz).strftime("%Y-%m-%d")

    print(f"\nFetching leads from {start_date} → {end_date} (one day at a time)...")
    from datetime import date as dt_date
    start_dt = dt_date.fromisoformat(start_date)
    end_dt   = dt_date.fromisoformat(end_date)
    frames = []
    cur = start_dt
    while cur <= end_dt:
        d = cur.isoformat()
        print(f"  Fetching {d}...", end=" ", flush=True)
        try:
            chunk = fetch_leads_range(d, d)
            print(f"{len(chunk)} rows")
            frames.append(chunk)
        except Exception as e:
            print(f"ERROR: {e}")
        cur = cur.replace(day=cur.day + 1) if cur.day < 28 else dt_date.fromordinal(cur.toordinal() + 1)

    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    # Deduplicate — keep last (most recent) entry per pre_user_id across days
    if not df.empty and "Pre User ID" in df.columns:
        df = df.drop_duplicates(subset=["Pre User ID"], keep="last")
    print(f"Total leads after dedup: {len(df)}")

    ql = df[df["Lead Type"].str.strip().str.upper() == "QL"]
    print(f"QL leads: {len(ql)}\n")

    # Sort ascending by form fill date so sheet rows are chronological
    if "Form Filled At IST" in ql.columns:
        ql = ql.sort_values("Form Filled At IST", ascending=True)

    no_call_ids    = get_no_call_ids()
    no_meeting_ids = get_no_meeting_ids()

    no_call_written = 0
    no_meeting_written = 0

    for _, row in ql.iterrows():
        uid = str(row.get("Pre User ID", "")).strip()
        if not uid or uid == "nan":
            continue

        entry = row.to_dict()
        form_filled      = _to_utc(row.get("Form Filled At IST"))
        call_started_raw = row.get("Latest AI Call Started At IST")
        call_time        = _to_utc(call_started_raw)
        call_is_null     = _is_null(call_started_raw)
        call_completed   = row.get("Call Completion")
        call_is_true     = (
            not _is_null(call_completed)
            and str(call_completed).strip() == "TRUE"
        )
        meeting_is_null  = _is_null(row.get("Meeting Booked At IST"))

        # No-call: form filled, call null
        if form_filled is not None and call_is_null and uid not in no_call_ids:
            append_no_call(entry)
            no_call_ids.add(uid)
            no_call_written += 1
            print(f"  [NO CALL]    {uid} — {row.get('Name')} | form filled {row.get('Form Filled At IST')}")

        # No-meeting: Call Completion='TRUE', meeting null
        if call_is_true and call_time is not None and meeting_is_null and uid not in no_meeting_ids:
            append_no_meeting(entry)
            no_meeting_ids.add(uid)
            no_meeting_written += 1
            print(f"  [NO MEETING] {uid} — {row.get('Name')} | call at {row.get('Latest AI Call Started At IST')}")

    print(f"\n{'─'*50}")
    print(f"No-call rows written:    {no_call_written}")
    print(f"No-meeting rows written: {no_meeting_written}")


if __name__ == "__main__":
    start = sys.argv[1] if len(sys.argv) > 1 else "2026-05-22"
    resync(start)
