from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from fastapi.responses import PlainTextResponse
import os
import logging
from metabase import fetch_leads
from logic import init_seen, run_checks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI()

RUN_SECRET = os.environ.get("RUN_SECRET", "")


@app.on_event("startup")
async def startup():
    try:
        df = fetch_leads()
        init_seen(df)
        logger.info("Startup dedup seed complete.")
    except Exception as e:
        logger.warning(f"Startup seed failed: {e}")


@app.get("/health")
def health():
    return {"status": "ok"}


def _run_job():
    try:
        df = fetch_leads()
        result = run_checks(df)
        logger.info(f"Run complete: {result}")
    except Exception as e:
        logger.error(f"Run failed: {e}", exc_info=True)


@app.post("/run")
def run(background_tasks: BackgroundTasks, x_run_secret: str | None = Header(default=None)):
    if RUN_SECRET and x_run_secret != RUN_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    background_tasks.add_task(_run_job)
    return PlainTextResponse("OK")
