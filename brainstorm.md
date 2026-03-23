# Project: Automated Job Hunter & AI CV Tailoring Agent (Zero-Cost Architecture)

## 📖 1. Project Overview
Building a fully automated AI Agent that acts as a personal job-hunting assistant. The system automatically scrapes job postings from LinkedIn, evaluates their match against the user's base CV, reports the best matches via Telegram, and automatically rewrites the CV for specific jobs with a single "OK" click, delivering the final tailored document directly to the user's email.

Key highlight: **Cost-effective (Zero-Cost)** serverless architecture, leveraging free tiers and local embedding models to minimize LLM API costs.

## ✨ 2. Core Features
* **Base CV Parsing:** Uses the user's base CV in Markdown format as the source of truth.
* **Smart Scraping & Filtering:** Scrapes new LinkedIn jobs, calculates similarity scores using Vector Embeddings, and filters down to the **top 5 most suitable jobs** daily.
* **Anti-Duplication:** Ensures the 5 selected jobs haven't been recommended in the last **15 days**.
* **Automated Logging:** Records all aggregated data and application statuses into Google Sheets.
* **Interactive Notifications:** Sends the curated job list to the user's Telegram with an inline "OK" button for each job.
* **Automated CV Tailoring & Email:** Upon clicking "OK", the AI Agent (via MCP) rewrites the CV to perfectly align with the specific Job Description (JD) and emails the final version to the user.

## 🏗️ 3. Tech Stack & Architecture
* **Data Scraper:** Python (BeautifulSoup / Selenium / `linkedin-api`).
* **Matching Engine (Zero-Cost):** Local Vector Embeddings (e.g., `sentence-transformers`, `all-MiniLM-L6-v2`) calculating Cosine Similarity.
* **Database:** Google Sheets API (for job history and status tracking).
* **User Interface (UI):** Telegram Bot API (Messaging & Webhook handling).
* **AI Engine:** MCP Server + LLM (Claude 3.5 Sonnet or GPT-4o) for intelligent CV tailoring.
* **Hosting/Runners (Serverless):**
    * **GitHub Actions:** Executes scheduled tasks (Cron jobs) and the CV generation workflow.
    * **Cloudflare Workers:** Acts as a lightweight proxy to catch Webhooks from Telegram and dispatch the GitHub Actions workflow.

## 🔄 4. Data Flow

### Flow 1: The Hunter (Automated Daily)
1. **GitHub Actions (Cron Job)** triggers at 8:00 AM daily.
2. A Python script scrapes the 50-100 latest JDs from LinkedIn.
3. Reads history from **Google Sheets** to filter out jobs seen in the last 15 days.
4. Converts the base CV and the new JDs into Vectors. Calculates Cosine Similarity to extract the **Top 5 highest-scoring jobs**.
5. Logs these 5 new jobs into Google Sheets.
6. Sends a summary message via the **Telegram Bot** (including an "OK" button tied to each Job ID).

### Flow 2: The Tailor (Triggered by "OK")
1. User clicks "OK" on a Telegram message.
2. Telegram fires a Webhook to **Cloudflare Workers**.
3. Cloudflare Workers triggers the `workflow_dispatch` API to wake up **GitHub Actions (Flow 2)**.
4. GitHub Actions retrieves the Job ID, fetches the corresponding JD from Google Sheets, and reads the base Markdown CV.
5. Activates the **AI Agent (via MCP Tools)** to tailor the CV based on the specific JD.
6. Exports the tailored CV (PDF/Markdown) and sends it via **Email** (SMTP).
7. Updates the status to "Applied" in Google Sheets.

## 🗺️ 5. Development Roadmap

### 🎯 Phase 1: MVP - The Hunter (Data & Recommendations Only)
*Goal: Every morning at 8:00 AM, Telegram receives exactly 5 highly relevant, non-duplicated jobs.*
* [ ] Set up the GitHub Repository, get the Telegram Bot Token, and generate the Google Service Account JSON credentials.
* [ ] Build the scraper script to fetch the latest ~50 LinkedIn jobs.
* [ ] Integrate Local Vector Embeddings to compare the base CV against JDs and extract the Top 5.
* [ ] Implement the 15-day deduplication logic using Google Sheets.
* [ ] Deploy to GitHub Actions as a daily Cron Job and ensure Telegram receives basic notifications (without buttons initially).

### 🎯 Phase 2: Version 1.0 - The Tailor (Agentic AI & Webhooks)
*Goal: Introduce the "OK" button. Clicking "OK" triggers the AI to write the CV and email it.*
* [ ] Deploy a Cloudflare Worker to catch Telegram Webhooks and dispatch the GitHub Actions workflow.
* [ ] Create the second GitHub Actions workflow (`tailor.yml`).
* [ ] Configure the MCP Server and provide Tools granting the AI Agent access to read JDs, read the base CV, and generate the new CV.
* [ ] Integrate a Python script to send emails via SMTP with the tailored CV attached.
* [ ] Add the interactive "OK" inline button to the Telegram Bot and perform End-to-End (E2E) testing.

### 🎯 Phase 3: Version 2.0 - Optimization & Expansion (Optional)
* [ ] Refine Prompt Engineering so the AI also writes a personalized Cover Letter to include in the email body.
* [ ] Expand scraping sources (integrate other regional job boards alongside LinkedIn).
* [ ] Enhance Error Handling (e.g., if LinkedIn changes its HTML structure, send an alert message to Telegram instead of silently failing).
