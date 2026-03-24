"""Semantic similarity scoring using sentence-transformers."""

import re
import logging
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    logger.info("Loading sentence-transformers model: %s", MODEL_NAME)
    return SentenceTransformer(MODEL_NAME)


def _clean_text(text: str) -> str:
    """Strip markdown symbols to produce cleaner embeddings."""
    text = re.sub(r"[#*`_~>]", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)  # [label](url) -> label
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def rank_jobs(cv_text: str, jobs: list[dict]) -> list[dict]:
    """
    Score each job's description against the CV and return jobs sorted by
    similarity_score descending. Modifies each job dict in-place to add the score.

    Args:
        cv_text: Raw CV text (Markdown is fine).
        jobs: List of job dicts, each must have a 'description' key.

    Returns:
        Same list, sorted by similarity_score descending.
    """
    if not jobs:
        return []

    model = _get_model()
    clean_cv = _clean_text(cv_text)

    logger.info("Encoding CV...")
    cv_vector = model.encode(clean_cv, convert_to_numpy=True)

    descriptions = [_clean_text(j.get("description", "")) for j in jobs]
    logger.info("Encoding %d job descriptions (batch)...", len(descriptions))
    jd_vectors = model.encode(descriptions, convert_to_numpy=True, batch_size=32)

    for job, jd_vec in zip(jobs, jd_vectors):
        job["similarity_score"] = round(_cosine_similarity(cv_vector, jd_vec), 4)

    jobs.sort(key=lambda j: j["similarity_score"], reverse=True)
    logger.info("Top score: %.4f | Bottom score: %.4f",
                jobs[0]["similarity_score"], jobs[-1]["similarity_score"])
    return jobs
