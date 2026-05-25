import logging
import pandas as pd
from datetime import datetime, timezone, timedelta
from sheets import (
    append_no_call, get_no_call_ids,
    append_no_meeting, get_no_meeting_ids,
)

logger = logging.getLogger(__name__)

WINDOW_MIN = 15

_seen_no_call: set[str] = set()
_seen_no_meeting: set[str] = set()

IST = timezone(timedelta(hours=5, minutes=30))


def _to_utc(dt) -> datetime | None:
    """Convert a naive IST pandas Timestamp to UTC. Returns None if null/invalid."""
    try:
        if dt is None:
            return None
        if pd.isna(dt):
            return None
        # pandas Timestamp with no tz — treat as IST
        if hasattr(dt, 'tzinfo') and dt.tzinfo is None:
            return dt.replace(tzinfo=IST).astimezone(timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _is_null(val) -> bool:
    if val is None:
        return True
    try:
        return bool(pd.isna(val))
    except Exception:
        return False


def _minutes_since(dt_utc: datetime) -> float:
    return (datetime.now(timezone.utc) - dt_utc).total_seconds() / 60


def init_seen(df: pd.DataFrame) -> None:
    _seen_no_call.update(get_no_call_ids())
    _seen_no_meeting.update(get_no_meeting_ids())


def run_checks(df: pd.DataFrame) -> dict:
    no_call_count = 0
    no_meeting_count = 0

    ql = df[df["Lead Type"].str.strip().str.upper() == "QL"]
    logger.info(f"QL leads to check: {len(ql)}")

    for _, row in ql.iterrows():
        uid = str(row.get("Pre User ID", "")).strip()
        if not uid or uid == "nan":
            continue

        entry = row.to_dict()

        # ── Alert 1: Form filled, call NOT started, 15 min elapsed ──────────
        form_filled = _to_utc(row.get("Form Filled At IST"))
        call_started_raw = row.get("Latest AI Call Started At IST")
        call_is_null = _is_null(call_started_raw)

        if (
            form_filled is not None          # form fill time exists
            and call_is_null                 # Latest AI Call Started At IST is blank
            and _minutes_since(form_filled) >= WINDOW_MIN   # 15 min elapsed since form fill
            and uid not in _seen_no_call
        ):
            logger.info(f"No-call: {uid} | form filled {_minutes_since(form_filled):.1f} min ago")
            append_no_call(entry)
            _seen_no_call.add(uid)
            no_call_count += 1

        # ── Alert 2: Call Completion='TRUE', meeting NOT booked, 15 min elapsed ─
        call_completed_raw = row.get("Call Completion")
        call_is_true = (
            not _is_null(call_completed_raw)
            and str(call_completed_raw).strip() == "TRUE"
        )
        call_time = _to_utc(row.get("Latest AI Call Started At IST"))
        meeting_is_null = _is_null(row.get("Meeting Booked At IST"))

        if (
            call_is_true                     # Call Completion == True
            and call_time is not None        # call timestamp exists
            and meeting_is_null              # Meeting Booked At IST is blank
            and _minutes_since(call_time) >= WINDOW_MIN    # 15 min elapsed since call
            and uid not in _seen_no_meeting
        ):
            logger.info(f"No-meeting: {uid} | call done {_minutes_since(call_time):.1f} min ago")
            append_no_meeting(entry)
            _seen_no_meeting.add(uid)
            no_meeting_count += 1

    return {
        "ql_leads_checked": len(ql),
        "no_call_alerts_sent": no_call_count,
        "no_meeting_alerts_sent": no_meeting_count,
    }
