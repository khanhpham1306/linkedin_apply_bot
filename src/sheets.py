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

JOB_HISTORY_HEADERS = [
    "job_id", "title", "company", "location", "url",
    "similarity_score", "recommended_date", "status",
    "telegram_message_id", "notes",
]

RUN_LOG_HEADERS = [
    "run_id", "run_timestamp", "jobs_scraped",
    "jobs_after_dedup", "jobs_recommended", "status", "error_message",
]


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


def append_recommendations(service_account_info: dict, sheet_id: str, jobs: list[dict]) -> None:
    """Append top recommended jobs to the job_history sheet."""
    client = _get_client(service_account_info)
    ss = client.open_by_key(sheet_id)
    ws = _get_or_create_sheet(ss, JOB_HISTORY_SHEET, JOB_HISTORY_HEADERS)

    today = datetime.now(timezone.utc).date().isoformat()
    rows = []
    for job in jobs:
        rows.append([
            job.get("job_id", ""),
            job.get("title", ""),
            job.get("company", ""),
            job.get("location", ""),
            job.get("apply_url", ""),
            str(job.get("similarity_score", "")),
            today,
            "RECOMMENDED",
            "",  # telegram_message_id (Phase 2)
            "",  # notes
        ])

    ws.append_rows(rows, value_input_option="USER_ENTERED")
    logger.info("Appended %d recommendations to '%s'.", len(rows), JOB_HISTORY_SHEET)


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
