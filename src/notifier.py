"""Telegram notification dispatch."""

import json
import logging
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _send(token: str, chat_id: str, text: str, reply_markup: dict | None = None) -> dict:
    """Send a message and return the parsed response JSON."""
    url = TELEGRAM_API.format(token=token, method="sendMessage")
    payload: dict = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    resp = requests.post(url, json=payload, timeout=15)
    resp.raise_for_status()
    logger.info("Telegram message sent (status %d).", resp.status_code)
    return resp.json()


def send_recommendations(
    token: str,
    chat_id: str,
    jobs: list[dict],
    run_stats: dict,
) -> int | None:
    """
    Send a consolidated job recommendations message with inline Apply buttons.

    Args:
        token: Telegram bot token.
        chat_id: Target chat or user ID.
        jobs: Ranked job list (top N).
        run_stats: Dict with keys: jobs_scraped, jobs_after_dedup, jobs_recommended.

    Returns:
        The Telegram message_id of the sent message, or None on failure.
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

    if jobs:
        lines.append("\n<i>Tap a button below to tailor your CV for that job:</i>")

    # Build inline keyboard: 3 buttons per row
    keyboard_rows: list[list[dict]] = []
    row: list[dict] = []
    for i, job in enumerate(jobs, start=1):
        job_id = job.get("job_id", "")
        row.append({"text": f"✅ Apply #{i}", "callback_data": f"apply:{job_id}"})
        if len(row) == 3:
            keyboard_rows.append(row)
            row = []
    if row:
        keyboard_rows.append(row)

    reply_markup = {"inline_keyboard": keyboard_rows} if keyboard_rows else None

    result = _send(token, chat_id, "\n".join(lines), reply_markup=reply_markup)
    message_id: int | None = result.get("result", {}).get("message_id")
    logger.info("Recommendation message sent, message_id=%s", message_id)
    return message_id


def send_error(token: str, chat_id: str, error: str) -> None:
    """Send an error alert to the Telegram chat."""
    text = f"<b>Job Hunter FAILED</b>\n\n<code>{error[:3000]}</code>"
    _send(token, chat_id, text)
