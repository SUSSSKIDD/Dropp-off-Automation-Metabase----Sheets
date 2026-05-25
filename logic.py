import pandas as pd
from datetime import datetime, timezone, timedelta
from telegram_client import alert_no_call, alert_no_meeting
from sheets import (
    append_no_call, get_no_call_ids,
    append_no_meeting, get_no_meeting_ids,
)

WINDOW_MIN = 15

_seen_no_call: set[str] = set()
_seen_no_meeting: set[str] = set()

IST = timezone(timedelta(hours=5, minutes=30))


def _to_utc(dt) -> datetime | None:
    try:
        if dt is None or (isinstance(dt, float) and pd.isna(dt)):
            return None
        if pd.isna(dt):
            return None
        if hasattr(dt, 'tzinfo') and dt.tzinfo is None:
            return dt.replace(tzinfo=IST).astimezone(timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _is_empty(val) -> bool:
    if val is None:
        return True
    try:
        return bool(pd.isna(val))
    except Exception:
        return False


def init_seen(df: pd.DataFrame) -> None:
    _seen_no_call.update(get_no_call_ids())
    _seen_no_meeting.update(get_no_meeting_ids())


def run_checks(df: pd.DataFrame) -> dict:
    now = datetime.now(timezone.utc)
    no_call_count = 0
    no_meeting_count = 0

    ql = df[df["Lead Type"].str.strip().str.upper() == "QL"]

    for _, row in ql.iterrows():
        uid = str(row.get("Pre User ID", "")).strip()
        if not uid or uid == "nan":
            continue

        entry = row.to_dict()
        form_filled  = _to_utc(row.get("Form Filled At IST"))
        call_time    = _to_utc(row.get("Latest Completed AI Call Started At IST"))
        call_empty   = _is_empty(row.get("Latest Completed AI Call Started At IST"))
        meeting_empty = _is_empty(row.get("Meeting Booked At IST"))

        # Alert 1: form filled but no call within 15 min
        if (
            form_filled is not None
            and call_empty
            and (now - form_filled).total_seconds() >= WINDOW_MIN * 60
            and uid not in _seen_no_call
        ):
            alert_no_call(entry)
            append_no_call(entry)
            _seen_no_call.add(uid)
            no_call_count += 1

        # Alert 2: Call Completion strictly True + no meeting booked within 15 min
        call_completed = row.get("Call Completion")
        call_is_true = call_completed is True or str(call_completed).strip().lower() == "true"

        if (
            call_is_true
            and call_time is not None
            and meeting_empty
            and (now - call_time).total_seconds() >= WINDOW_MIN * 60
            and uid not in _seen_no_meeting
        ):
            alert_no_meeting(entry)
            append_no_meeting(entry)
            _seen_no_meeting.add(uid)
            no_meeting_count += 1

    return {
        "ql_leads_checked": len(ql),
        "no_call_alerts_sent": no_call_count,
        "no_meeting_alerts_sent": no_meeting_count,
    }
