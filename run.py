import schedule
import time
import logging
from dotenv import load_dotenv
load_dotenv()

from metabase import fetch_leads
from logic import init_seen, run_checks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def job():
    try:
        logger.info("Fetching leads from MetaBase...")
        df = fetch_leads()
        result = run_checks(df)
        logger.info(f"Done: {result}")
    except Exception as e:
        logger.error(f"Job failed: {e}", exc_info=True)


if __name__ == "__main__":
    logger.info("Starting lead alert worker...")

    # Seed dedup from Google Sheet on startup so restarts don't re-alert
    try:
        df = fetch_leads()
        init_seen(df)
        logger.info("Startup dedup seed complete.")
    except Exception as e:
        logger.warning(f"Startup seed failed (will continue): {e}")

    schedule.every(20).minutes.do(job)
    logger.info("Scheduler running — checking every 20 minutes.")

    # Run once immediately so today's backlog is processed on startup
    job()

    while True:
        schedule.run_pending()
        time.sleep(30)
