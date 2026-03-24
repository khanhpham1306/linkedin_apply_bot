"""Tests for the sheets module (deduplication logic only, no real API calls)."""

from datetime import date, timedelta, timezone, datetime
from unittest.mock import MagicMock, patch

from src.sheets import get_seen_job_ids


def _make_row(job_id: str, days_ago: int) -> list[str]:
    rec_date = (datetime.now(timezone.utc) - timedelta(days=days_ago)).date().isoformat()
    return [job_id, "Title", "Company", "Location", "url", "0.85", rec_date, "RECOMMENDED", "", ""]


@patch("src.sheets._get_client")
def test_get_seen_job_ids_within_window(mock_client):
    mock_ws = MagicMock()
    mock_ws.get_all_values.return_value = [
        ["job_id", "title", "company", "location", "url", "score", "recommended_date", "status", "msg_id", "notes"],
        _make_row("job_001", 5),   # 5 days ago - within 15-day window
        _make_row("job_002", 14),  # 14 days ago - within window
        _make_row("job_003", 16),  # 16 days ago - outside window
    ]
    mock_ss = MagicMock()
    mock_ss.worksheet.return_value = mock_ws
    mock_client.return_value.open_by_key.return_value = mock_ss

    seen = get_seen_job_ids({}, "fake-sheet-id", days=15)

    assert "job_001" in seen
    assert "job_002" in seen
    assert "job_003" not in seen


@patch("src.sheets._get_client")
def test_get_seen_job_ids_empty_sheet(mock_client):
    mock_ws = MagicMock()
    mock_ws.get_all_values.return_value = [
        ["job_id", "title", "company", "location", "url", "score", "recommended_date", "status", "msg_id", "notes"],
    ]
    mock_ss = MagicMock()
    mock_ss.worksheet.return_value = mock_ws
    mock_client.return_value.open_by_key.return_value = mock_ss

    seen = get_seen_job_ids({}, "fake-sheet-id", days=15)
    assert seen == set()
