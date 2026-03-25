"""Main orchestrator: sequences all modules end-to-end."""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from src import config as cfg
from src import cv_parser, embeddings, notifier, scraper, sheets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

CV_PATH = Path(__file__).parent.parent / "data" / "cv.md"
CONFIG_PATH = Path(__file__).parent.parent / "config.json"


def _load_search_config() -> dict:
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open() as f:
            return json.load(f)
    return {
        "search_queries": [],
        "jobs_to_scrape_per_query": 50,
        "top_n_recommendations": 5,
        "dedup_window_days": 15,
    }


def run() -> None:
    conf = cfg.load()
    search_conf = _load_search_config()
    top_n: int = search_conf.get("top_n_recommendations", 5)
    dedup_days: int = search_conf.get("dedup_window_days", 15)
    limit_per_query: int = search_conf.get("jobs_to_scrape_per_query", 50)

    run_timestamp = datetime.now(timezone.utc).isoformat()
    run_data = {
        "run_id": conf.github_run_id,
        "run_timestamp": run_timestamp,
        "jobs_scraped": 0,
        "jobs_after_dedup": 0,
        "jobs_recommended": 0,
        "status": "FAILED",
        "error_message": "",
    }

    try:
        # 1. Load CV
        cv_text = CV_PATH.read_text(encoding="utf-8")
        logger.info("CV loaded (%d chars).", len(cv_text))

        # 2. Resolve search queries (config override or CV-derived)
        search_queries = search_conf.get("search_queries") or []
        if not search_queries:
            default_location = "Vietnam"
            search_queries = cv_parser.extract_search_queries(
                cv_text, default_location, conf.anthropic_api_key
            )
        if not search_queries:
            raise RuntimeError(
                "No search queries available. Set search_queries in config.json "
                "or provide ANTHROPIC_API_KEY so they can be derived from the CV."
            )

        # 3. Scrape LinkedIn
        all_jobs: list[dict] = []
        seen_ids_within_scrape: set[str] = set()
        for query in search_queries:
            logger.info("Scraping: %s in %s", query["keywords"], query["location"])
            fetched = scraper.fetch_jobs(
                keywords=query["keywords"],
                location=query["location"],
                limit=limit_per_query,
            )
            # Deduplicate within the same run (same job can appear in multiple queries)
            for job in fetched:
                if job["job_id"] not in seen_ids_within_scrape:
                    seen_ids_within_scrape.add(job["job_id"])
                    all_jobs.append(job)

        run_data["jobs_scraped"] = len(all_jobs)
        logger.info("Total unique jobs scraped: %d", len(all_jobs))

        # 4. Deduplication against Sheets history
        service_account_info = conf.google_service_account_info()
        sheets_available = True
        try:
            seen_ids = sheets.get_seen_job_ids(
                service_account_info, conf.google_sheet_id, days=dedup_days
            )
        except PermissionError as exc:
            logger.warning(
                "Google Sheets API unavailable (check that the API is enabled and "
                "the service account has access): %s. Skipping deduplication.", exc
            )
            seen_ids = set()
            sheets_available = False

        new_jobs = [j for j in all_jobs if j["job_id"] not in seen_ids]
        run_data["jobs_after_dedup"] = len(new_jobs)
        logger.info("Jobs after dedup: %d", len(new_jobs))

        if not new_jobs:
            logger.warning("No new jobs after deduplication. Nothing to recommend.")
            run_data["status"] = "SUCCESS"
            run_data["jobs_recommended"] = 0
            if sheets_available:
                sheets.append_run_log(service_account_info, conf.google_sheet_id, run_data)
            notifier.send_recommendations(
                conf.telegram_bot_token, conf.telegram_chat_id,
                [], run_data,
            )
            return

        # 5. Score jobs against CV
        ranked = embeddings.rank_jobs(cv_text, new_jobs)
        top_jobs = ranked[:top_n]
        run_data["jobs_recommended"] = len(top_jobs)

        # 6. Write recommendations to Sheets
        if sheets_available:
            sheets.append_recommendations(service_account_info, conf.google_sheet_id, top_jobs)

        # 7. Write run log
        run_data["status"] = "SUCCESS"
        if sheets_available:
            sheets.append_run_log(service_account_info, conf.google_sheet_id, run_data)

        # 8. Send Telegram notification
        notifier.send_recommendations(
            conf.telegram_bot_token, conf.telegram_chat_id,
            top_jobs, run_data,
        )
        logger.info("Run completed successfully. Recommended %d jobs.", len(top_jobs))

    except Exception as exc:
        logger.exception("Run failed: %s", exc)
        run_data["status"] = "FAILED"
        run_data["error_message"] = str(exc)

        # Best-effort: try to log to Sheets and notify Telegram
        if not isinstance(exc, PermissionError):
            try:
                service_account_info = conf.google_service_account_info()
                sheets.append_run_log(service_account_info, conf.google_sheet_id, run_data)
            except Exception as sheet_exc:
                logger.error("Could not write run_log after failure: %s", sheet_exc)

        try:
            notifier.send_error(conf.telegram_bot_token, conf.telegram_chat_id, str(exc))
        except Exception as tg_exc:
            logger.error("Could not send Telegram error notification: %s", tg_exc)

        sys.exit(1)


if __name__ == "__main__":
    run()
