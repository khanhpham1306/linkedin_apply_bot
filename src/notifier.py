"""Telegram notification dispatch."""

import logging
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def _send(token: str, chat_id: str, text: str) -> None:
    url = TELEGRAM_API.format(token=token)
    resp = requests.post(
        url,
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        timeout=15,
    )
    resp.raise_for_status()
    logger.info("Telegram message sent (status %d).", resp.status_code)


def send_recommendations(
    token: str,
    chat_id: str,
    jobs: list[dict],
    run_stats: dict,
) -> None:
    """
    Send a consolidated job recommendations message.

    Args:
        token: Telegram bot token.
        chat_id: Target chat or user ID.
        jobs: Ranked job list (top N).
        run_stats: Dict with keys: jobs_scraped, jobs_after_dedup, jobs_recommended.
    """
    today = datetime.now(timezone.utc).strftime("%-d %b %Y")
    lines = [f"<b>Job Recommendations - {today}</b>\n"]

    for i, job in enumerate(jobs, start=1):
        score = job.get("similarity_score", 0)
        lines.append(
            f"{i}. <b>{job.get('title', 'Unknown')}</b> @ {job.get('company', 'Unknown')}\n"
            f"   {job.get('location', '')} | Score: {score:.4f}\n"
            f"   {job.get('apply_url', '')}"
        )

    lines.append(
        f"\nScraped: {run_stats.get('jobs_scraped', 0)} jobs | "
        f"After dedup: {run_stats.get('jobs_after_dedup', 0)} | "
        f"Recommended: {run_stats.get('jobs_recommended', 0)}"
    )

    if run_stats.get("jobs_recommended", 0) < 5:
        lines.append(
            f"\n<i>Note: Only {run_stats.get('jobs_recommended', 0)} new jobs found "
            f"(fewer than the target of 5).</i>"
        )

    _send(token, chat_id, "\n".join(lines))


def send_error(token: str, chat_id: str, error: str) -> None:
    """Send an error alert to the Telegram chat."""
    text = f"<b>Job Hunter FAILED</b>\n\n<code>{error[:3000]}</code>"
    _send(token, chat_id, text)
