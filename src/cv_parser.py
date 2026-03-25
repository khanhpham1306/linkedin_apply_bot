"""Extract LinkedIn search queries from CV text using Claude API, with file-based caching."""

import hashlib
import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_CACHE_PATH = Path(__file__).parent.parent / "data" / "derived_queries.json"
_MODEL = "claude-haiku-4-5-20251001"

_PROMPT = """\
You are a career assistant. Read the CV below and identify the 3 most relevant LinkedIn job search keywords that match the person's PRIMARY profession — their main career track, not their tools or side skills.

Rules:
- Focus on job titles and business functions (e.g. "Strategy Manager", "Retail Operations Manager")
- Do NOT use programming languages, software tools, or certifications as keywords
- Each keyword should be a short phrase suitable for a LinkedIn job search (2-4 words max)
- Return ONLY a JSON array of 3 strings, nothing else

CV:
{cv_text}

Response (JSON array only):"""


def _cv_hash(cv_text: str) -> str:
    return hashlib.sha256(cv_text.encode("utf-8")).hexdigest()


def _load_cache() -> dict:
    if _CACHE_PATH.exists():
        try:
            return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_cache(cv_hash: str, queries: list[dict]) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(
        json.dumps({"cv_hash": cv_hash, "queries": queries}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def extract_search_queries(cv_text: str, location: str, api_key: str) -> list[dict]:
    """Return search query dicts derived from the CV.

    Uses a cache file so Claude is only called when the CV content has changed.
    Returns an empty list if the API key is missing or the API call fails.
    """
    current_hash = _cv_hash(cv_text)

    cache = _load_cache()
    if cache.get("cv_hash") == current_hash and cache.get("queries"):
        logger.info("CV unchanged — using cached search queries.")
        return cache["queries"]

    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set; cannot derive queries from CV.")
        return []

    logger.info("CV changed (or no cache found) — calling Claude to extract job titles.")
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=_MODEL,
            max_tokens=128,
            messages=[{"role": "user", "content": _PROMPT.format(cv_text=cv_text)}],
        )
        raw = message.content[0].text.strip()
        # Strip markdown code fences that some models add despite instructions
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*\n?", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            raw = raw.strip()
        logger.debug("Raw Claude response: %r", raw)
        if not raw:
            logger.error("Claude returned an empty response; cannot extract queries.")
            return []
        keywords_list: list[str] = json.loads(raw)
        queries = [{"keywords": kw, "location": location} for kw in keywords_list]
        _save_cache(current_hash, queries)
        logger.info("Extracted queries: %s", [q["keywords"] for q in queries])
        return queries
    except Exception as exc:
        logger.error("Failed to extract queries from CV via Claude: %s", exc)
        return []
