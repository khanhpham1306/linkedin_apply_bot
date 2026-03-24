"""Tests for the scraper module."""

from unittest.mock import patch

import pandas as pd
import pytest

from src.scraper import ScraperError, _normalize, fetch_jobs


def _make_df(rows: list[dict]) -> pd.DataFrame:
    """Helper: build a minimal JobSpy-style DataFrame."""
    return pd.DataFrame(rows)


def test_normalize_basic():
    df = _make_df([
        {
            "id": "3901234567",
            "title": "Python Engineer",
            "company": "Acme Corp",
            "location": "Ho Chi Minh City",
            "job_url": "https://www.linkedin.com/jobs/view/3901234567/",
            "description": "Write Python code.",
        }
    ])
    jobs = _normalize(df)
    assert len(jobs) == 1
    assert jobs[0]["job_id"] == "3901234567"
    assert jobs[0]["title"] == "Python Engineer"
    assert jobs[0]["company"] == "Acme Corp"
    assert jobs[0]["apply_url"] == "https://www.linkedin.com/jobs/view/3901234567/"
    assert jobs[0]["description"] == "Write Python code."
    assert "scraped_at" in jobs[0]


def test_normalize_skips_missing_id():
    df = _make_df([
        {"id": "", "title": "Bad Job", "company": "Nobody", "location": "", "job_url": "", "description": ""},
        {"id": "1234", "title": "Good Job", "company": "Someone", "location": "", "job_url": "", "description": ""},
    ])
    jobs = _normalize(df)
    assert len(jobs) == 1
    assert jobs[0]["job_id"] == "1234"


def test_normalize_empty_df():
    df = pd.DataFrame()
    jobs = _normalize(df)
    assert jobs == []


def test_fetch_jobs_returns_normalized_list():
    df = _make_df([
        {
            "id": "999",
            "title": "Data Engineer",
            "company": "TechCo",
            "location": "Vietnam",
            "job_url": "https://www.linkedin.com/jobs/view/999/",
            "description": "Build pipelines.",
        }
    ])
    with patch("src.scraper.scrape_jobs", return_value=df) as mock_scrape:
        result = fetch_jobs(keywords="Data Engineer", location="Vietnam", limit=10, hours_old=24)

    mock_scrape.assert_called_once_with(
        site_name=["linkedin"],
        search_term="Data Engineer",
        location="Vietnam",
        results_wanted=10,
        hours_old=24,
    )
    assert len(result) == 1
    assert result[0]["job_id"] == "999"


def test_fetch_jobs_empty_result():
    with patch("src.scraper.scrape_jobs", return_value=pd.DataFrame()):
        result = fetch_jobs(keywords="Nonexistent", location="Mars")
    assert result == []


def test_fetch_jobs_retries_on_exception():
    with patch("src.scraper.scrape_jobs", side_effect=RuntimeError("network error")), \
         patch("src.scraper.time.sleep"):
        with pytest.raises(ScraperError, match="3 attempts"):
            fetch_jobs(keywords="X", location="Y")


def test_scraper_error_is_exception():
    err = ScraperError("test error")
    assert isinstance(err, Exception)
    assert str(err) == "test error"
