"""LinkedIn job scraper using JobSpy — no LinkedIn account required."""

import logging
import time
from datetime import datetime, timezone

import pandas as pd
from jobspy import scrape_jobs

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """Raised when scraping fails after all retries."""


def fetch_jobs(
    keywords: str,
    location: str,
    limit: int = 50,
    hours_old: int = 24,
) -> list[dict]:
    """
    Fetch recent LinkedIn job postings matching keywords and location.

    No LinkedIn account is required — uses LinkedIn's public guest API via JobSpy.

    Args:
        keywords: Job search keywords, e.g. "Python Backend Engineer".
        location: Location string, e.g. "Ho Chi Minh City, Vietnam".
        limit: Maximum number of jobs to retrieve.
        hours_old: Only jobs posted within this many hours (default: 24h).

    Returns:
        List of job dicts with keys:
            job_id, title, company, location, apply_url, description, scraped_at
    """
    last_error = None
    for attempt in range(1, 4):
        try:
            return _do_fetch(keywords, location, limit, hours_old)
        except ScraperError:
            raise
        except Exception as exc:
            last_error = exc
            wait = 2 ** attempt
            logger.warning(
                "Scraper attempt %d/%d failed: %s — retrying in %ds",
                attempt, 3, exc, wait,
            )
            time.sleep(wait)

    raise ScraperError(
        f"LinkedIn scraping failed after 3 attempts. Last error: {last_error}"
    )


def _do_fetch(
    keywords: str,
    location: str,
    limit: int,
    hours_old: int,
) -> list[dict]:
    df = scrape_jobs(
        site_name=["linkedin"],
        search_term=keywords,
        location=location,
        results_wanted=limit,
        hours_old=hours_old,
    )

    if df is None or df.empty:
        logger.info("LinkedIn search returned 0 jobs for '%s' in '%s'.", keywords, location)
        return []

    jobs = _normalize(df)
    logger.info("Fetched %d jobs from LinkedIn.", len(jobs))
    return jobs


def _normalize(df: pd.DataFrame) -> list[dict]:
    """Convert a JobSpy DataFrame to the project's standard job dict format."""
    scraped_at = datetime.now(timezone.utc).isoformat()
    jobs = []
    for _, row in df.iterrows():
        job_id = str(row.get("id", "")).strip()
        if not job_id or job_id == "nan":
            continue
        jobs.append({
            "job_id": job_id,
            "title": str(row.get("title", "Unknown Title")),
            "company": str(row.get("company", "Unknown Company")),
            "location": str(row.get("location", "")),
            "apply_url": str(row.get("job_url", "")),
            "description": str(row.get("description", "")),
            "scraped_at": scraped_at,
        })
    return jobs
