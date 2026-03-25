# Project Todo: Automated Job Hunter & AI CV Tailoring Agent

> **Goal:** A fully automated, zero-cost AI agent that scrapes LinkedIn daily, ranks jobs against your CV, notifies you on Telegram, and tailors your CV with one click.

---

## Phase 1 — MVP: The Hunter `[IN PROGRESS]`
**Goal:** Every morning at 08:00 AM (UTC+7), Telegram receives exactly 5 highly relevant, non-duplicated job recommendations.

### Code (Done)
- [x] Set up repository structure (`src/`, `data/`, `tests/`, `.github/`)
- [x] Write `src/scraper.py` — LinkedIn job fetching via `python-jobspy` (no LinkedIn account needed) with retry logic
- [x] Write `src/embeddings.py` — semantic scoring with `all-MiniLM-L6-v2`, batch encoding, cosine similarity
- [x] Write `src/sheets.py` — Google Sheets deduplication (15-day window), job history log, run log
- [x] Write `src/notifier.py` — consolidated Telegram message dispatch (one message per run)
- [x] Write `src/config.py` — centralised env var loading with fail-fast validation
- [x] Write `src/cv_parser.py` — auto-derives LinkedIn search queries from CV text via Claude Haiku (cached in `data/derived_queries.json`)
- [x] Write `src/runner.py` — end-to-end orchestrator sequencing all modules; gracefully degrades if Sheets API unavailable
- [x] Write `.github/workflows/hunter.yml` — daily cron at 01:00 UTC (08:00 UTC+7), pip + HuggingFace model caching, failure notification step
- [x] Write `config.json` — search queries and tuning parameters (version-controlled; queries here override CV-derived ones)
- [x] Write `data/cv.md` — real CV (Pham Gia Khanh) as source of truth for similarity scoring
- [x] Write `tests/` — unit tests for embeddings, scraper parsing, and Sheets dedup logic
- [x] Write `CLAUDE.md` — architecture and dev command reference for Claude Code
- [x] Pin all dependencies in `requirements.txt`

### Infrastructure Setup (Pending — manual steps)
- [ ] Create a **Google Cloud project**, enable Sheets API, create a service account, download JSON key
- [ ] Create the **Google Sheets spreadsheet** (`job_history`, `run_log`, `bot_state` tabs auto-created on first run)
- [ ] Create a **Telegram Bot** via BotFather and retrieve your personal Chat ID
- [ ] Add all 4 **GitHub Secrets** to the repository:
  - `GOOGLE_SERVICE_ACCOUNT_JSON`
  - `GOOGLE_SHEET_ID`
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`

### Validation (Pending)
- [ ] Trigger workflow manually via `workflow_dispatch` and confirm it runs end-to-end
- [ ] Verify Telegram receives the daily message with 5 ranked jobs
- [ ] Verify Google Sheets `job_history` and `run_log` tabs are populated correctly
- [ ] Confirm 15-day dedup works on the second run (previously seen jobs filtered out)

---

## Phase 2 — Version 1.0: The Tailor `[IN PROGRESS]`
**Goal:** Add inline Apply buttons to each Telegram job card. Tapping triggers AI to rewrite the CV for that specific JD and return the tailored CV as a file in Telegram.

**Architecture (no Cloudflare Worker needed):**
- GitHub Actions poller runs once daily at 20:00 UTC+7 via cron, calls Telegram `getUpdates`, processes button callbacks
- Offset (last processed update_id) is persisted in a `bot_state` Google Sheet tab
- Job descriptions are stored (truncated to 5 000 chars) in `job_history` sheet so Claude has context
- Tailored CV delivered as a `.md` file directly in Telegram (no SMTP/email required)

### Code (Done)
- [x] Add **"✅ Apply #N" inline buttons** to each job in the Telegram notification (`src/notifier.py`)
- [x] Update `src/sheets.py` — store `telegram_message_id` & `description` per job; `get_job_by_id`; `update_job_status`; `get/set_bot_state`
- [x] Create `src/tailor.py` — AI-powered CV rewriting using Claude `claude-sonnet-4-6`
- [x] Create `src/poller.py` — polls Telegram `getUpdates`, handles `apply:{job_id}` callbacks end-to-end; warns user if re-applying to an already-applied job
- [x] Create `.github/workflows/poller.yml` — runs once daily at 20:00 UTC+7, uses lightweight `requirements-tailor.txt`
- [x] Create `requirements-tailor.txt` — minimal deps (anthropic, gspread, google-auth, requests)

### Infrastructure Setup (Pending — manual steps)
- [ ] Add `ANTHROPIC_API_KEY` to GitHub repository secrets
- [ ] Enable the poller workflow in GitHub Actions (it auto-starts on push to default branch)
- [ ] End-to-end test: tap "✅ Apply #N" → poller picks up callback → Claude rewrites CV → `.md` file arrives in Telegram → Sheets status → `APPLIED`

---

## Phase 3 — Version 2.0: Optimization & Expansion `[NOT STARTED]`
**Goal:** Make the system smarter, broader, and more polished.

- [ ] Refine prompt engineering so the AI also writes a **personalized cover letter** included in the email body
- [ ] Expand scraping to additional **regional job boards** (e.g., VietnamWorks, TopCV, JobStreet) alongside LinkedIn
- [ ] Improve scraper resilience — detect LinkedIn blocks early and send a Telegram alert instead of silently failing
- [ ] Add a **similarity score threshold** filter (e.g., skip jobs scoring below 0.40) to reduce noise
- [ ] Add **multi-language support** for job searches in Vietnamese

---

## Quick Reference — Secrets Checklist

| Secret | Phase | Description |
|---|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | 1 | Full service account JSON as a single-line string |
| `GOOGLE_SHEET_ID` | 1 | ID from the Google Sheets URL |
| `TELEGRAM_BOT_TOKEN` | 1 | From BotFather |
| `TELEGRAM_CHAT_ID` | 1 | Your personal Telegram user ID |
| `ANTHROPIC_API_KEY` | 1+2 | For CV-derived search queries (Phase 1, optional) and Claude-powered CV tailoring (Phase 2, required) |
