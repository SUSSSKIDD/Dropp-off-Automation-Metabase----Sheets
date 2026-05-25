import os
import requests

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"


def _fmt(val) -> str:
    if val is None or (isinstance(val, float) and val != val):
        return "—"
    return str(val)


def _send(text: str) -> None:
    resp = requests.post(
        API_URL,
        json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
        timeout=10,
    )
    resp.raise_for_status()
    if not resp.json().get("ok"):
        raise Exception(f"Telegram error: {resp.json().get('description')}")


def alert_no_call(entry: dict) -> None:
    msg = (
        "🔴 <b>No Call Alert</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Name:</b>              {_fmt(entry.get('Name'))}\n"
        f"🆔 <b>Pre User ID:</b>       {_fmt(entry.get('Pre User ID'))}\n"
        f"📞 <b>Phone:</b>             {_fmt(entry.get('Phone'))}\n"
        f"🎓 <b>Education:</b>         {_fmt(entry.get('Highest Level Education'))}\n"
        f"✈️  <b>Preferred Intake:</b>  {_fmt(entry.get('Preferred Intake'))}\n"
        f"📅 <b>Form Filled At:</b>    {_fmt(entry.get('Form Filled At IST'))}\n\n"
        "⚠️ No call started within 15 min of form fill."
    )
    _send(msg)


def alert_no_meeting(entry: dict) -> None:
    msg = (
        "🟡 <b>No Meeting Alert</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Name:</b>              {_fmt(entry.get('Name'))}\n"
        f"🆔 <b>Pre User ID:</b>       {_fmt(entry.get('Pre User ID'))}\n"
        f"📞 <b>Phone:</b>             {_fmt(entry.get('Phone'))}\n"
        f"🎓 <b>Education:</b>         {_fmt(entry.get('Highest Level Education'))}\n"
        f"✈️  <b>Preferred Intake:</b>  {_fmt(entry.get('Preferred Intake'))}\n"
        f"📅 <b>Form Filled At:</b>    {_fmt(entry.get('Form Filled At IST'))}\n"
        f"📞 <b>Call Completed At:</b> {_fmt(entry.get('Latest AI Call Started At IST'))}\n\n"
        "⚠️ No meeting booked within 15 min of call completion."
    )
    _send(msg)
