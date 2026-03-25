# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install all dependencies (hunter workflow)
pip install -r requirements.txt

# Install lightweight dependencies (poller/tailor workflow only)
pip install -r requirements-tailor.txt

# Run the full job hunter pipeline
python -m src.runner

# Run the Telegram poller (processes Apply button callbacks)
python -m src.poller

# Run all tests
pytest

# Run a single test file
pytest tests/test_embeddings.py

# Run a single test by name
pytest tests/test_embeddings.py::test_rank_jobs_adds_score_and_sorts
```

## Environment Variables

Copy `.env.template` and populate before running locally. Required vars:
- `GOOGLE_SERVICE_ACCOUNT_JSON` — full service account JSON as a single-line string
- `GOOGLE_SHEET_ID` — ID from the Google Sheets URL
- `TELEGRAM_BOT_TOKEN` — from BotFather
- `TELEGRAM_CHAT_ID` — your personal Telegram user ID

Optional:
- `ANTHROPIC_API_KEY` — needed for CV tailoring (`src/poller.py`) and for auto-deriving search queries from the CV when `config.json` has no `search_queries`

## Architecture

Two independent pipelines, each driven by a GitHub Actions workflow:

### Pipeline 1 — Job Hunter (`src/runner.py`, daily at 08:00 UTC+7)
1. Loads CV from `data/cv.md`
2. Resolves search queries from `config.json` (or derives them via Claude if empty)
3. Scrapes LinkedIn via `python-jobspy` (no LinkedIn account needed) — `src/scraper.py`
4. Deduplicates against a 15-day rolling window in Google Sheets — `src/sheets.py`
5. Ranks remaining jobs by cosine similarity (CV vs JD) using `all-MiniLM-L6-v2` — `src/embeddings.py`
6. Sends top-N jobs to Telegram with inline "✅ Apply #N" buttons — `src/notifier.py`
7. Persists job records (including `description` and `telegram_message_id`) to the `job_history` sheet

### Pipeline 2 — Telegram Poller (`src/poller.py`, every 30 min)
1. Reads `last_update_id` offset from the `bot_state` Google Sheet
2. Calls Telegram `getUpdates` to find `apply:{job_id}` callback queries
3. Fetches job details (including stored JD) from `job_history` sheet
4. Calls Claude `claude-sonnet-4-6` to tailor the CV — `src/tailor.py`
5. Sends the tailored CV as a `.md` file via Telegram `sendDocument`
6. Updates job status to `APPLIED` in Sheets; persists new offset

### Google Sheets Schema
Three tabs, auto-created on first run:
- `job_history` — one row per recommended job; columns include `job_id`, `status`, `telegram_message_id`, `description`
- `run_log` — one row per hunter run with counts and status
- `bot_state` — key/value table; currently stores `last_update_id` for the poller offset

### Key Design Decisions
- `requirements-tailor.txt` is a minimal subset of `requirements.txt` used by the poller workflow to avoid downloading `sentence-transformers` and its heavy ML deps when only the Claude API is needed.
- The scraper uses `python-jobspy` (public LinkedIn guest API), so no LinkedIn credentials are required.
- If `ANTHROPIC_API_KEY` is absent, the hunter still runs (using hardcoded `config.json` queries); only CV tailoring is disabled.
- Job descriptions are truncated to 5,000 chars in Sheets storage and 4,000 chars when passed to Claude.
- `config.json` controls search queries, scrape limit per query, top-N recommendations, and dedup window — edit this file to tune behaviour without touching code.
