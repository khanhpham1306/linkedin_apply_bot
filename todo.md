# Project Todo: Automated Job Hunter & AI CV Tailoring Agent

> **Goal:** A fully automated, zero-cost AI agent that scrapes LinkedIn daily, ranks jobs against your CV, notifies you on Telegram, and tailors your CV with one click.

---

## Phase 1 — MVP: The Hunter `[IN PROGRESS]`
**Goal:** Every morning at 08:00 AM (UTC+7), Telegram receives exactly 5 highly relevant, non-duplicated job recommendations.

### Code (Done)
- [x] Set up repository structure (`src/`, `data/`, `tests/`, `.github/`)
- [x] Write `src/scraper.py` — LinkedIn job fetching via `linkedin-api` with retry logic
- [x] Write `src/embeddings.py` — semantic scoring with `all-MiniLM-L6-v2`, batch encoding, cosine similarity
- [x] Write `src/sheets.py` — Google Sheets deduplication (15-day window), job history log, run log
- [x] Write `src/notifier.py` — consolidated Telegram message dispatch (one message per run)
- [x] Write `src/config.py` — centralised env var loading with fail-fast validation
- [x] Write `src/runner.py` — end-to-end orchestrator sequencing all modules
- [x] Write `.github/workflows/hunter.yml` — daily cron at 01:00 UTC (08:00 UTC+7), pip + HuggingFace model caching, failure notification step
- [x] Write `config.json` — search queries and tuning parameters (version-controlled)
- [x] Write `data/cv.md` — real CV (Pham Gia Khanh) as source of truth for similarity scoring
- [x] Write `tests/` — unit tests for embeddings, scraper parsing, and Sheets dedup logic
- [x] Pin all dependencies in `requirements.txt`

### Infrastructure Setup (Pending — manual steps)
- [ ] Create a **burner LinkedIn account** (use a separate email, not your main account)
- [ ] Create a **Google Cloud project**, enable Sheets API, create a service account, download JSON key
- [ ] Create the **Google Sheets spreadsheet** (two tabs: `job_history`, `run_log` will be auto-created on first run)
- [ ] Create a **Telegram Bot** via BotFather and retrieve your personal Chat ID
- [ ] Add all 6 **GitHub Secrets** to the repository:
  - `LINKEDIN_EMAIL`
  - `LINKEDIN_PASSWORD`
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

## Phase 2 — Version 1.0: The Tailor `[NOT STARTED]`
**Goal:** Add an "OK" inline button to each Telegram job card. Clicking it triggers AI to rewrite the CV for that specific JD and email the tailored PDF.

- [ ] Deploy a **Cloudflare Worker** to receive Telegram Webhooks and call the GitHub Actions `workflow_dispatch` API
- [ ] Register the Telegram Webhook URL pointing at the Cloudflare Worker
- [ ] Add **"OK" inline buttons** to each job in the Telegram notification (`src/notifier.py`)
- [ ] Create `src/tailor.py` — AI-powered CV rewriting using Claude API (MCP tools) against a specific JD
- [ ] Create `.github/workflows/tailor.yml` — workflow triggered by `workflow_dispatch` with `job_id` input
- [ ] Create `src/mailer.py` — SMTP email dispatch with the tailored CV (PDF/Markdown) attached
- [ ] Update `src/sheets.py` — store `telegram_message_id` per job; update status to `APPLIED` after email sent
- [ ] Store new secrets: `ANTHROPIC_API_KEY` (or `OPENAI_API_KEY`), `SMTP_USER`, `SMTP_PASSWORD`, `CLOUDFLARE_WORKER_URL`
- [ ] End-to-end test: click "OK" → Cloudflare → GitHub Actions → AI rewrites CV → email arrives

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
| `LINKEDIN_EMAIL` | 1 | Burner LinkedIn account email |
| `LINKEDIN_PASSWORD` | 1 | Burner LinkedIn account password |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | 1 | Full service account JSON as a single-line string |
| `GOOGLE_SHEET_ID` | 1 | ID from the Google Sheets URL |
| `TELEGRAM_BOT_TOKEN` | 1 | From BotFather |
| `TELEGRAM_CHAT_ID` | 1 | Your personal Telegram user ID |
| `ANTHROPIC_API_KEY` | 2 | For Claude-powered CV tailoring |
| `SMTP_USER` | 2 | Email address used to send tailored CVs |
| `SMTP_PASSWORD` | 2 | App password for the SMTP email account |
| `CLOUDFLARE_WORKER_URL` | 2 | Public URL of the deployed Cloudflare Worker |
