"""AI-powered CV tailoring using Claude API."""

import logging

import anthropic

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096
DESCRIPTION_CHAR_LIMIT = 4000


def tailor_cv(cv_text: str, job: dict, api_key: str) -> str:
    """
    Rewrite the base CV to be optimally tailored for a specific job posting.

    Rules enforced in the prompt:
    - No fabrication: only reframe/reorder existing experience
    - Highlight relevant skills and achievements using JD keywords
    - Rewrite the Professional Summary to target this specific role
    - Output clean Markdown

    Args:
        cv_text: The base CV in Markdown format.
        job: Dict with keys: title, company, location, apply_url, description.
        api_key: Anthropic API key.

    Returns:
        Tailored CV as a Markdown string.
    """
    client = anthropic.Anthropic(api_key=api_key)

    description = (job.get("description") or "No description available.")[:DESCRIPTION_CHAR_LIMIT]

    prompt = f"""You are an expert career coach and CV writer specialising in executive and management roles.

Your task: rewrite the CV below so it is perfectly tailored for the job posting provided.

STRICT RULES — follow every one without exception:
1. Do NOT invent, fabricate, or exaggerate any experience, skill, achievement, or date.
2. You may reorder bullet points and sections to put the most relevant experience first.
3. Rewrite the Executive Summary (2–3 sentences) to directly address the target role.
4. Naturally weave keywords from the job description into existing bullet points where truthful.
5. Keep the same overall Markdown structure. The CV has these sections in order: Executive Summary, Key Achievements, Awards and Leadership, Professional Experience, Education, Technical Skills & Languages. Do not remove or reorder sections. You may reorder bullet points within a section.
6. Do not add a "Skills" section if one does not already exist.
7. Output ONLY the tailored CV in Markdown — no commentary, no preamble.
8. Do not modify the Key Achievements section — those metrics must remain factually unchanged.

---

TARGET JOB:
Title:    {job.get("title", "")}
Company:  {job.get("company", "")}
Location: {job.get("location", "")}
URL:      {job.get("apply_url", "")}

JOB DESCRIPTION:
{description}

---

BASE CV:
{cv_text}

---

Tailored CV (Markdown):"""

    logger.info("Calling Claude %s to tailor CV for %s @ %s", MODEL, job.get("title"), job.get("company"))
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    tailored = message.content[0].text
    logger.info(
        "CV tailoring complete. Input tokens: %d, output tokens: %d.",
        message.usage.input_tokens,
        message.usage.output_tokens,
    )
    return tailored
