import os
import json
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

NO_CALL_SHEET_ID    = os.environ["NO_CALL_SHEET_ID"]
NO_MEETING_SHEET_ID = os.environ["NO_MEETING_SHEET_ID"]

_SERVICE_ACCOUNT_JSON = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]

NO_CALL_HEADERS = [
    "Pre User ID", "Name", "Phone",
    "Preferred Intake", "Highest Level Education", "Form Filled At IST",
    "Airo Link",
]

AIRO_LINK_COL = 7  # column G (1-based)

NO_MEETING_HEADERS = [
    "Pre User ID", "Name", "Phone",
    "Preferred Intake", "Highest Level Education",
    "Form Filled At IST", "Latest AI Call Started At IST",
]

_client: gspread.Client | None = None
_ws_no_call: gspread.Worksheet | None = None
_ws_no_meeting: gspread.Worksheet | None = None


def _get_client() -> gspread.Client:
    global _client
    if _client is None:
        creds = Credentials.from_service_account_info(
            json.loads(_SERVICE_ACCOUNT_JSON), scopes=SCOPES
        )
        _client = gspread.authorize(creds)
    return _client


def _get_ws(sheet_id: str, headers: list, cache_attr: str) -> gspread.Worksheet:
    ws = _get_client().open_by_key(sheet_id).sheet1
    if not ws.get_all_values() or ws.cell(1, 1).value != "Pre User ID":
        ws.clear()
        ws.append_row(headers, value_input_option="RAW")
    return ws


def _get_no_call_ws() -> gspread.Worksheet:
    global _ws_no_call
    if _ws_no_call is None:
        _ws_no_call = _get_ws(NO_CALL_SHEET_ID, NO_CALL_HEADERS, "_ws_no_call")
        # Ensure Airo Link header exists on existing sheets without clearing data
        if _ws_no_call.cell(1, AIRO_LINK_COL).value != "Airo Link":
            _ws_no_call.update_cell(1, AIRO_LINK_COL, "Airo Link")
    return _ws_no_call


def _get_no_meeting_ws() -> gspread.Worksheet:
    global _ws_no_meeting
    if _ws_no_meeting is None:
        _ws_no_meeting = _get_ws(NO_MEETING_SHEET_ID, NO_MEETING_HEADERS, "_ws_no_meeting")
    return _ws_no_meeting


def _v(entry: dict, key: str) -> str:
    val = entry.get(key)
    if val is None or (isinstance(val, float) and val != val):
        return ""
    return str(val)


def append_no_call(entry: dict) -> None:
    row = [
        _v(entry, "Pre User ID"), _v(entry, "Name"), _v(entry, "Phone"),
        _v(entry, "Preferred Intake"), _v(entry, "Highest Level Education"),
        _v(entry, "Form Filled At IST"),
    ]
    _get_no_call_ws().append_row(row, value_input_option="USER_ENTERED")


def append_no_meeting(entry: dict) -> None:
    row = [
        _v(entry, "Pre User ID"), _v(entry, "Name"), _v(entry, "Phone"),
        _v(entry, "Preferred Intake"), _v(entry, "Highest Level Education"),
        _v(entry, "Form Filled At IST"),
        _v(entry, "Latest AI Call Started At IST"),
    ]
    _get_no_meeting_ws().append_row(row, value_input_option="USER_ENTERED")


def get_no_call_ids() -> set[str]:
    rows = _get_no_call_ws().get_all_values()
    return {str(r[0]).strip() for r in rows[1:] if r and r[0]}


def get_no_meeting_ids() -> set[str]:
    rows = _get_no_meeting_ws().get_all_values()
    return {str(r[0]).strip() for r in rows[1:] if r and r[0]}


def get_rows_missing_airo_link() -> list[tuple[int, str]]:
    """Returns (1-based row number, pre_user_id) for no-call rows where Airo Link is blank."""
    rows = _get_no_call_ws().get_all_values()
    result = []
    for i, row in enumerate(rows[1:], start=2):
        pre_user_id = row[0].strip() if row else ""
        if not pre_user_id:
            continue
        airo_link = row[AIRO_LINK_COL - 1] if len(row) >= AIRO_LINK_COL else ""
        if not airo_link.strip() or airo_link.strip() == "API ERROR":
            result.append((i, pre_user_id))
    return result


def update_airo_link(row_num: int, value: str) -> None:
    _get_no_call_ws().update_cell(row_num, AIRO_LINK_COL, value)
