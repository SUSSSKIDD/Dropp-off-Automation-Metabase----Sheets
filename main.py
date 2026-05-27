from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from fastapi.responses import PlainTextResponse
import os
import time
import logging
from metabase import fetch_leads
from logic import init_seen, run_checks
from mixpanel import fetch_airo_link
from sheets import get_rows_missing_airo_link, update_airo_link

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


_ENRICH_PER_RUN = 50  # stay under Mixpanel's 60 JQL queries/hour limit


def _enrich_airo_links():
    try:
        rows = get_rows_missing_airo_link()[:_ENRICH_PER_RUN]
        logger.info(f"Airo link enrichment: {len(rows)} rows to process")
        for row_num, pre_user_id in rows:
            url = fetch_airo_link(pre_user_id)
            update_airo_link(row_num, url)
            time.sleep(1.0)
        logger.info(f"Airo link enrichment complete: {len(rows)} rows updated")
    except Exception as e:
        logger.error(f"Airo link enrichment failed: {e}", exc_info=True)


def _run_job():
    try:
        df = fetch_leads()
        result = run_checks(df)
        logger.info(f"Run complete: {result}")
    except Exception as e:
        logger.error(f"Run failed: {e}", exc_info=True)
    _enrich_airo_links()


@app.post("/run")
def run(background_tasks: BackgroundTasks, x_run_secret: str | None = Header(default=None)):
    if RUN_SECRET and x_run_secret != RUN_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    background_tasks.add_task(_run_job)
    return PlainTextResponse("OK")
