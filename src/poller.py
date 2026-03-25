"""
Telegram update poller — processes inline button callback queries.

Flow when user taps "✅ Apply #N":
  1. getUpdates  →  find callback_query with data="apply:{job_id}"
  2. answerCallbackQuery  →  clear the spinner on the button
  3. Send "⏳ Tailoring…" status message
  4. Fetch job details from Google Sheets
  5. Call src/tailor.py → Claude API → tailored CV (Markdown)
  6. Send tailored CV as a .md file via Telegram sendDocument
  7. Update Sheets status → "APPLIED"
  8. Persist new Telegram update offset in bot_state sheet
"""

import io
import logging
import sys
from pathlib import Path

import requests

from src import config as cfg, sheets, tailor

logger = logging.getLogger(__name__)

CV_PATH = Path(__file__).parent.parent / "data" / "cv.md"
LAST_UPDATE_ID_KEY = "last_update_id"
TELEGRAM_BASE = "https://api.telegram.org/bot{token}/{method}"


# ---------------------------------------------------------------------------
# Telegram helpers
# ---------------------------------------------------------------------------

def _tg_url(token: str, method: str) -> str:
    return TELEGRAM_BASE.format(token=token, method=method)


def _get_updates(token: str, offset: int) -> list[dict]:
    """Fetch pending updates from Telegram (non-blocking, filter callback_query only)."""
    resp = requests.get(
        _tg_url(token, "getUpdates"),
        params={
            "offset": offset,
            "timeout": 0,
            "allowed_updates": '["callback_query"]',
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("result", [])


def _answer_callback(token: str, callback_query_id: str, text: str = "") -> None:
    """Acknowledge a callback query to clear the loading spinner."""
    requests.post(
        _tg_url(token, "answerCallbackQuery"),
        json={"callback_query_id": callback_query_id, "text": text},
        timeout=10,
    )


def _send_message(token: str, chat_id: str, text: str) -> None:
    requests.post(
        _tg_url(token, "sendMessage"),
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        timeout=15,
    )


def _send_document(
    token: str, chat_id: str, content: str, filename: str, caption: str = ""
) -> None:
    """Upload a text file as a Telegram document."""
    requests.post(
        _tg_url(token, "sendDocument"),
        data={"chat_id": chat_id, "caption": caption[:1024]},
        files={"document": (filename, io.BytesIO(content.encode("utf-8")), "text/markdown")},
        timeout=60,
    )


# ---------------------------------------------------------------------------
# Core apply handler
# ---------------------------------------------------------------------------

def _handle_apply(
    token: str,
    chat_id: str,
    job_id: str,
    service_account_info: dict,
    sheet_id: str,
    cv_text: str,
    anthropic_api_key: str,
) -> None:
    """End-to-end handler: tailor CV and send back to user."""
    # 1. Fetch job from Sheets
    job = sheets.get_job_by_id(service_account_info, sheet_id, job_id)
    if not job:
        _send_message(
            token, chat_id,
            f"❌ Job <code>{job_id}</code> not found in history. It may have expired.",
        )
        logger.warning("Job %s not found in Sheets.", job_id)
        return

    title = job.get("title", "Unknown Role")
    company = job.get("company", "Unknown Company")

    # 2. Confirm click received; warn if CV was already sent for this job
    if job.get("status") == "APPLIED":
        _send_message(
            token, chat_id,
            f"✅ Got your apply request for <b>{title}</b> @ {company}!\n"
            f"ℹ️ You've already applied for this job before — re-tailoring and re-sending your CV now.\n"
            f"⏳ This usually takes 20–40 seconds.",
        )
    else:
        _send_message(
            token, chat_id,
            f"✅ Got your apply request for <b>{title}</b> @ {company}!\n"
            f"⏳ Tailoring your CV now — this usually takes 20–40 seconds.",
        )

    # 3. Tailor CV via Claude
    if not anthropic_api_key:
        _send_message(token, chat_id, "❌ <code>ANTHROPIC_API_KEY</code> is not configured.")
        return

    try:
        tailored_cv = tailor.tailor_cv(cv_text, job, anthropic_api_key)
    except Exception as exc:
        logger.exception("CV tailoring failed for job %s: %s", job_id, exc)
        _send_message(token, chat_id, f"❌ CV tailoring failed:\n<code>{str(exc)[:500]}</code>")
        return

    # 4. Send tailored CV as .md document
    safe_company = "".join(c if c.isalnum() else "_" for c in company)
    filename = f"CV_{safe_company}_{job_id}.md"
    caption = f"✅ Tailored CV — {title} @ {company}"
    _send_document(token, chat_id, tailored_cv, filename, caption)
    logger.info("Tailored CV sent for job %s.", job_id)

    # 5. Update Sheets status
    try:
        sheets.update_job_status(service_account_info, sheet_id, job_id, "APPLIED")
    except Exception as exc:
        logger.warning("Could not update Sheets status for job %s: %s", job_id, exc)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )

    conf = cfg.load()
    service_account_info = conf.google_service_account_info()

    # Read last processed update_id from Sheets
    try:
        last_id_str = sheets.get_bot_state(service_account_info, conf.google_sheet_id, LAST_UPDATE_ID_KEY)
        offset = int(last_id_str) + 1 if last_id_str else 0
    except Exception as exc:
        logger.warning("Could not read last_update_id from Sheets (%s). Starting from 0.", exc)
        offset = 0

    logger.info("Polling Telegram updates with offset=%d", offset)
    updates = _get_updates(conf.telegram_bot_token, offset)

    if not updates:
        logger.info("No new updates.")
        return

    cv_text = CV_PATH.read_text(encoding="utf-8")
    max_update_id = offset - 1

    for update in updates:
        update_id: int = update["update_id"]
        max_update_id = max(max_update_id, update_id)

        callback_query = update.get("callback_query")
        if not callback_query:
            continue

        callback_id: str = callback_query["id"]
        data: str = callback_query.get("data", "")

        if not data.startswith("apply:"):
            _answer_callback(conf.telegram_bot_token, callback_id, "Unknown action.")
            continue

        job_id = data.split(":", 1)[1]
        logger.info("Received apply callback for job_id=%s", job_id)

        # Acknowledge immediately so the button stops spinning
        _answer_callback(conf.telegram_bot_token, callback_id, "⏳ On it!")

        _handle_apply(
            token=conf.telegram_bot_token,
            chat_id=conf.telegram_chat_id,
            job_id=job_id,
            service_account_info=service_account_info,
            sheet_id=conf.google_sheet_id,
            cv_text=cv_text,
            anthropic_api_key=conf.anthropic_api_key,
        )

    # Persist the new offset so next poll skips already-processed updates
    new_offset = max_update_id + 1
    try:
        sheets.set_bot_state(
            service_account_info, conf.google_sheet_id, LAST_UPDATE_ID_KEY, str(new_offset)
        )
        logger.info("Saved last_update_id offset=%d to Sheets.", new_offset)
    except Exception as exc:
        logger.warning("Could not save offset to Sheets: %s", exc)

    logger.info("Processed %d updates.", len(updates))


if __name__ == "__main__":
    run()
