"""Tests for the embeddings module."""

import pytest
from src.embeddings import _clean_text, _cosine_similarity, rank_jobs
import numpy as np


def test_clean_text_strips_markdown():
    raw = "# Title\n**bold** and _italic_ with `code`"
    result = _clean_text(raw)
    assert "#" not in result
    assert "*" not in result
    assert "`" not in result


def test_clean_text_removes_links():
    raw = "See [this page](https://example.com) for details."
    result = _clean_text(raw)
    assert "this page" in result
    assert "https://example.com" not in result


def test_cosine_similarity_identical():
    v = np.array([1.0, 0.0, 0.0])
    assert _cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal():
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    assert _cosine_similarity(a, b) == pytest.approx(0.0)


def test_cosine_similarity_zero_vector():
    a = np.array([0.0, 0.0])
    b = np.array([1.0, 0.0])
    assert _cosine_similarity(a, b) == 0.0


def test_rank_jobs_empty():
    assert rank_jobs("some cv text", []) == []


def test_rank_jobs_adds_score_and_sorts():
    cv = "Python backend engineer with FastAPI and PostgreSQL experience"
    jobs = [
        {
            "job_id": "1",
            "title": "iOS Developer",
            "description": "Swift and Xcode mobile development for iOS applications",
        },
        {
            "job_id": "2",
            "title": "Python Engineer",
            "description": "FastAPI Python backend development with PostgreSQL and Docker",
        },
    ]
    ranked = rank_jobs(cv, jobs)
    assert len(ranked) == 2
    assert "similarity_score" in ranked[0]
    assert "similarity_score" in ranked[1]
    # Python job should score higher than iOS job
    assert ranked[0]["job_id"] == "2"
    assert ranked[0]["similarity_score"] >= ranked[1]["similarity_score"]
