"""Tests for the scraper module."""

from src.scraper import _build_apply_url, _extract_description, ScraperError


def test_build_apply_url():
    url = _build_apply_url("3901234567")
    assert url == "https://www.linkedin.com/jobs/view/3901234567/"


def test_extract_description_dict():
    detail = {"description": {"text": "We are looking for a Python engineer."}}
    assert _extract_description(detail) == "We are looking for a Python engineer."


def test_extract_description_string():
    detail = {"description": "Plain text description"}
    assert _extract_description(detail) == "Plain text description"


def test_extract_description_missing():
    assert _extract_description({}) == ""


def test_extract_description_nested_missing():
    detail = {"description": {}}
    assert _extract_description(detail) == ""


def test_scraper_error_is_exception():
    err = ScraperError("test error")
    assert isinstance(err, Exception)
    assert str(err) == "test error"
