"""LinkedIn job scraper using the unofficial linkedin-api library."""

import logging
import time
from datetime import datetime, timezone

from linkedin_api import Linkedin

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """Raised when scraping fails after all retries."""


def _build_apply_url(job_id: str) -> str:
    return f"https://www.linkedin.com/jobs/view/{job_id}/"


def _extract_description(job_detail: dict) -> str:
    """Extract plain-text description from a job detail response."""
    try:
        desc = job_detail.get("description", {})
        # The API returns description as a dict with 'text' key
        if isinstance(desc, dict):
            return desc.get("text", "")
        return str(desc)
    except Exception:
        return ""


def fetch_jobs(
    email: str,
    password: str,
    keywords: str,
    location: str,
    limit: int = 50,
    listed_at: int = 86400,
) -> list[dict]:
    """
    Fetch recent LinkedIn job postings matching keywords and location.

    Args:
        email: LinkedIn account email (throwaway account recommended).
        password: LinkedIn account password.
        keywords: Job search keywords, e.g. "Python Backend Engineer".
        location: Location string, e.g. "Ho Chi Minh City, Vietnam".
        limit: Maximum number of raw jobs to retrieve before filtering.
        listed_at: Only jobs posted within this many seconds (default: 24h).

    Returns:
        List of job dicts with keys:
            job_id, title, company, location, apply_url, description, scraped_at
    """
    last_error = None
    for attempt in range(1, 4):
        try:
            return _do_fetch(email, password, keywords, location, limit, listed_at)
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
    email: str,
    password: str,
    keywords: str,
    location: str,
    limit: int,
    listed_at: int,
) -> list[dict]:
    api = Linkedin(email, password)

    raw_jobs = api.search_jobs(
        keywords=keywords,
        location_name=location,
        limit=limit,
        listed_at=listed_at,
    )

    if not raw_jobs:
        logger.info("LinkedIn search returned 0 jobs.")
        return []

    jobs = []
    scraped_at = datetime.now(timezone.utc).isoformat()

    for raw in raw_jobs:
        job_id = raw.get("trackingUrn", "").split(":")[-1]
        if not job_id:
            # Fallback: try entityUrn
            job_id = raw.get("entityUrn", "").split(":")[-1]
        if not job_id:
            continue

        # Fetch full job detail for description
        try:
            detail = api.get_job(job_id)
        except Exception as exc:
            logger.warning("Could not fetch detail for job %s: %s", job_id, exc)
            detail = {}

        title = (
            detail.get("title")
            or raw.get("title", "Unknown Title")
        )

        company_name = ""
        company_data = detail.get("companyDetails", {})
        if isinstance(company_data, dict):
            company_name = (
                company_data.get("com.linkedin.voyager.deco.jobs.web.shared"
                                  ".WebCompactJobPostingCompany", {})
                .get("companyResolutionResult", {})
                .get("name", "")
            )
        if not company_name:
            company_name = raw.get("companyName", "Unknown Company")

        location_str = detail.get("formattedLocation") or location
        description = _extract_description(detail)

        jobs.append({
            "job_id": job_id,
            "title": title,
            "company": company_name,
            "location": location_str,
            "apply_url": _build_apply_url(job_id),
            "description": description,
            "scraped_at": scraped_at,
        })

    logger.info("Fetched %d jobs from LinkedIn.", len(jobs))
    return jobs
