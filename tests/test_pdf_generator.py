"""Tests for src/pdf_generator.py"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

CV_PATH = Path(__file__).parent.parent / "data" / "cv.md"


def test_markdown_to_pdf_returns_valid_pdf():
    """markdown_to_pdf should return bytes starting with the PDF magic header."""
    from src.pdf_generator import markdown_to_pdf

    md_text = CV_PATH.read_text(encoding="utf-8")
    result = markdown_to_pdf(md_text)

    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF", "Output does not start with PDF magic bytes"
    assert len(result) > 1000, "PDF output is suspiciously small"


def test_markdown_to_pdf_minimal_input():
    """markdown_to_pdf works with a minimal markdown string."""
    from src.pdf_generator import markdown_to_pdf

    result = markdown_to_pdf("# Hello\n\n## Section\n\n- item one\n- item two\n")

    assert result[:4] == b"%PDF"
    assert len(result) > 500


def test_render_html_contains_expected_tags():
    """_render_html should produce h1, h2, h3, ul elements from CV markdown."""
    from src.pdf_generator import _render_html

    md = "# Name\n\n## Experience\n\n### Job Title\n\n- bullet\n"
    html = _render_html(md)

    assert "<h1>" in html
    assert "<h2" in html
    assert "<h3>" in html
    assert "<li>" in html


def test_poller_falls_back_to_md_on_pdf_failure(monkeypatch):
    """If pdf_generator.markdown_to_pdf raises, _handle_apply sends .md instead."""
    import src.poller as poller
    import src.pdf_generator as pdf_generator

    # Stub out external calls
    monkeypatch.setattr(poller, "_send_message", lambda *a, **kw: None)
    monkeypatch.setattr(poller, "_send_pdf_document", MagicMock())
    sent_md = []
    monkeypatch.setattr(
        poller,
        "_send_document",
        lambda token, chat_id, content, filename, caption="": sent_md.append(filename),
    )
    monkeypatch.setattr(
        poller.sheets,
        "get_job_by_id",
        lambda *a, **kw: {"title": "Engineer", "company": "Acme", "status": "NEW", "description": "desc"},
    )
    monkeypatch.setattr(poller.sheets, "update_job_status", lambda *a, **kw: None)
    monkeypatch.setattr(poller.tailor, "tailor_cv", lambda *a, **kw: "# Tailored CV\n")

    # Make markdown_to_pdf raise to trigger the .md fallback path
    monkeypatch.setattr(pdf_generator, "markdown_to_pdf", MagicMock(side_effect=RuntimeError("render failed")))

    poller._handle_apply(
        token="tok",
        chat_id="123",
        job_id="job42",
        service_account_info={},
        sheet_id="sheet1",
        cv_text="# CV\n",
        anthropic_api_key="key",
    )

    assert len(sent_md) == 1
    assert sent_md[0].endswith(".md"), f"Expected .md fallback, got: {sent_md[0]}"
