"""Google Sheets integration for job history and run logging."""

import logging
from datetime import datetime, timezone, timedelta

import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

JOB_HISTORY_SHEET = "job_history"
RUN_LOG_SHEET = "run_log"
BOT_STATE_SHEET = "bot_state"

JOB_HISTORY_HEADERS = [
    "job_id", "title", "company", "location", "url",
    "similarity_score", "recommended_date", "status",
    "telegram_message_id", "notes", "description",
]

RUN_LOG_HEADERS = [
    "run_id", "run_timestamp", "jobs_scraped",
    "jobs_after_dedup", "jobs_recommended", "status", "error_message",
]

BOT_STATE_HEADERS = ["key", "value"]


def _get_client(service_account_info: dict) -> gspread.Client:
    creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_or_create_sheet(spreadsheet: gspread.Spreadsheet, title: str, headers: list[str]):
    """Return worksheet by title, creating it with headers if it doesn't exist."""
    try:
        ws = spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=title, rows=1000, cols=len(headers))
        ws.append_row(headers, value_input_option="USER_ENTERED")
        logger.info("Created sheet '%s' with headers.", title)
    return ws


def get_seen_job_ids(service_account_info: dict, sheet_id: str, days: int = 15) -> set[str]:
    """
    Return the set of job_ids that have been recommended within the last `days` days.
    """
    client = _get_client(service_account_info)
    ss = client.open_by_key(sheet_id)
    ws = _get_or_create_sheet(ss, JOB_HISTORY_SHEET, JOB_HISTORY_HEADERS)

    all_rows = ws.get_all_values()
    if len(all_rows) <= 1:
        return set()

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).date()
    seen: set[str] = set()

    for row in all_rows[1:]:  # skip header
        if len(row) < 7:
            continue
        job_id = row[0].strip()
        date_str = row[6].strip()
        if not job_id or not date_str:
            continue
        try:
            rec_date = datetime.fromisoformat(date_str).date()
        except ValueError:
            try:
                from datetime import date
                rec_date = date.fromisoformat(date_str)
            except ValueError:
                continue
        if rec_date >= cutoff:
            seen.add(job_id)

    logger.info("Found %d job_ids seen in the last %d days.", len(seen), days)
    return seen


def append_recommendations(
    service_account_info: dict,
    sheet_id: str,
    jobs: list[dict],
    telegram_message_id: int | None = None,
) -> None:
    """Append top recommended jobs to the job_history sheet."""
    client = _get_client(service_account_info)
    ss = client.open_by_key(sheet_id)
    ws = _get_or_create_sheet(ss, JOB_HISTORY_SHEET, JOB_HISTORY_HEADERS)

    today = datetime.now(timezone.utc).date().isoformat()
    rows = []
    for job in jobs:
        description = job.get("description", "") or ""
        rows.append([
            job.get("job_id", ""),
            job.get("title", ""),
            job.get("company", ""),
            job.get("location", ""),
            job.get("apply_url", ""),
            str(job.get("similarity_score", "")),
            today,
            "RECOMMENDED",
            str(telegram_message_id) if telegram_message_id else "",
            "",  # notes
            description[:5000],  # truncate long descriptions
        ])

    ws.append_rows(rows, value_input_option="USER_ENTERED")
    logger.info("Appended %d recommendations to '%s'.", len(rows), JOB_HISTORY_SHEET)


def get_job_by_id(service_account_info: dict, sheet_id: str, job_id: str) -> dict | None:
    """Fetch a job's stored details by job_id. Returns None if not found."""
    client = _get_client(service_account_info)
    ss = client.open_by_key(sheet_id)
    ws = _get_or_create_sheet(ss, JOB_HISTORY_SHEET, JOB_HISTORY_HEADERS)

    all_rows = ws.get_all_values()
    if len(all_rows) <= 1:
        return None

    headers = all_rows[0]
    for row in all_rows[1:]:
        if not row or row[0].strip() != job_id:
            continue
        row_dict = dict(zip(headers, row))
        return {
            "job_id": row_dict.get("job_id", ""),
            "title": row_dict.get("title", ""),
            "company": row_dict.get("company", ""),
            "location": row_dict.get("location", ""),
            "apply_url": row_dict.get("url", ""),
            "description": row_dict.get("description", ""),
        }
    return None


def update_job_status(
    service_account_info: dict, sheet_id: str, job_id: str, status: str
) -> None:
    """Update the status column for a given job_id in job_history."""
    client = _get_client(service_account_info)
    ss = client.open_by_key(sheet_id)
    ws = _get_or_create_sheet(ss, JOB_HISTORY_SHEET, JOB_HISTORY_HEADERS)

    all_rows = ws.get_all_values()
    status_col = 8  # 1-indexed column for "status"

    for i, row in enumerate(all_rows[1:], start=2):  # skip header; rows are 1-indexed
        if row and row[0].strip() == job_id:
            ws.update_cell(i, status_col, status)
            logger.info("Updated job %s status → %s (row %d).", job_id, status, i)
            return

    logger.warning("Job %s not found in '%s' for status update.", job_id, JOB_HISTORY_SHEET)


def get_bot_state(service_account_info: dict, sheet_id: str, key: str) -> str:
    """Read a key-value pair from the bot_state sheet. Returns '' if key not found."""
    client = _get_client(service_account_info)
    ss = client.open_by_key(sheet_id)
    ws = _get_or_create_sheet(ss, BOT_STATE_SHEET, BOT_STATE_HEADERS)

    for row in ws.get_all_values()[1:]:
        if len(row) >= 2 and row[0].strip() == key:
            return row[1].strip()
    return ""


def set_bot_state(service_account_info: dict, sheet_id: str, key: str, value: str) -> None:
    """Upsert a key-value pair in the bot_state sheet."""
    client = _get_client(service_account_info)
    ss = client.open_by_key(sheet_id)
    ws = _get_or_create_sheet(ss, BOT_STATE_SHEET, BOT_STATE_HEADERS)

    all_rows = ws.get_all_values()
    for i, row in enumerate(all_rows[1:], start=2):
        if row and row[0].strip() == key:
            ws.update_cell(i, 2, value)
            logger.info("bot_state updated: %s = %s", key, value)
            return

    ws.append_row([key, value], value_input_option="USER_ENTERED")
    logger.info("bot_state inserted: %s = %s", key, value)


def append_run_log(service_account_info: dict, sheet_id: str, run_data: dict) -> None:
    """Append a run summary row to the run_log sheet."""
    client = _get_client(service_account_info)
    ss = client.open_by_key(sheet_id)
    ws = _get_or_create_sheet(ss, RUN_LOG_SHEET, RUN_LOG_HEADERS)

    row = [
        run_data.get("run_id", ""),
        run_data.get("run_timestamp", ""),
        str(run_data.get("jobs_scraped", 0)),
        str(run_data.get("jobs_after_dedup", 0)),
        str(run_data.get("jobs_recommended", 0)),
        run_data.get("status", ""),
        run_data.get("error_message", ""),
    ]
    ws.append_row(row, value_input_option="USER_ENTERED")
    logger.info("Run log appended: status=%s", run_data.get("status"))
