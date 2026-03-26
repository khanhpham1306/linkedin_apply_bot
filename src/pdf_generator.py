"""
Convert a Markdown CV string to a professionally styled PDF (bytes).

Usage:
    from src.pdf_generator import markdown_to_pdf
    pdf_bytes = markdown_to_pdf(md_text)
"""

import base64
import re
from pathlib import Path

import markdown as _markdown
from weasyprint import HTML as _HTML

_PHOTO_PATH = Path(__file__).parent.parent / "profile_image.jpg"

_CSS = """
@page {
    size: A4;
    margin: 18mm 20mm 18mm 20mm;
}

* {
    box-sizing: border-box;
}

body {
    font-family: "Liberation Sans", Arial, Helvetica, sans-serif;
    font-size: 10pt;
    color: #222222;
    line-height: 1.30;
    margin: 0;
    padding: 0;
}

/* ── Name / header ── */
h1 {
    font-size: 20pt;
    font-weight: 800;
    color: #0f4c81;
    border-bottom: 2.5pt solid #0f4c81;
    padding-bottom: 5pt;
    margin: 0 0 2pt 0;
    line-height: 1.15;
}

/* Subtitle line (bold paragraph right after name) */
h1 + p {
    font-size: 11pt;
    color: #1a1a2e;
    font-weight: 600;
    margin: 0 0 2pt 0;
    letter-spacing: 0.03em;
}

/* Contact line (second paragraph after name) */
h1 + p + p {
    font-size: 8.5pt;
    color: #555555;
    margin: 0 0 10pt 0;
}

/* ── Profile photo (floated top-right of header) ── */
.profile-photo-wrapper {
    float: right;
    margin: 0 0 6pt 12pt;
}

.profile-photo {
    width: 82pt;
    height: 82pt;
    border-radius: 50%;
    object-fit: cover;
    border: 2pt solid #0f4c81;
    display: block;
}

/* ── Section headings ── */
h2 {
    clear: both;
    font-size: 10.5pt;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #0f4c81;
    border-bottom: 0.75pt solid #0f4c81;
    margin: 8pt 0 2pt 0;
    padding-bottom: 2pt;
    page-break-after: avoid;
}

/* ── Job title / sub-section headings ── */
h3 {
    font-size: 10pt;
    font-weight: bold;
    color: #1a1a2e;
    margin: 5pt 0 1pt 0;
    page-break-after: avoid;
}

/* ── Body paragraphs ── */
p {
    margin: 0 0 4pt 0;
}

/* ── Bullet lists ── */
ul {
    margin: 2pt 0 4pt 0;
    padding-left: 16pt;
}

li {
    margin: 1pt 0;
    line-height: 1.3;
}

/* ── Inline bold / italic ── */
strong {
    font-weight: bold;
    color: #1a1a2e;
}

em {
    font-style: italic;
}

/* ── Key Achievements highlight box ── */
#key-achievements + ul {
    background: #f0f4fa;
    border-left: 3pt solid #0f4c81;
    padding: 6pt 10pt 6pt 16pt;
    margin: 3pt 0 6pt 0;
    list-style: none;
}

#key-achievements + ul li {
    margin: 3pt 0;
    padding-left: 0;
}

#key-achievements + ul li::before {
    content: "\\25b8  ";
    color: #0f4c81;
    font-weight: bold;
}

/* ── Awards inline styling ── */
#awards-and-leadership + ul {
    list-style: none;
    padding-left: 0;
}

#awards-and-leadership + ul li {
    margin: 1pt 0;
    padding-left: 0;
}

#awards-and-leadership + ul li::before {
    content: "\\2605  ";
    color: #0f4c81;
    font-size: 8pt;
}
"""

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>{css}</style>
</head>
<body>
{body}
</body>
</html>
"""


def _photo_data_url() -> str | None:
    """Return a base64 data URL for the profile photo, or None if file is missing."""
    if not _PHOTO_PATH.exists():
        return None
    b64 = base64.b64encode(_PHOTO_PATH.read_bytes()).decode()
    return f"data:image/jpeg;base64,{b64}"


def _add_heading_ids(html: str) -> str:
    """Add id attributes to h2 elements based on their slugified text content."""

    def _slugify(match: re.Match) -> str:
        text = match.group(1)
        slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
        return f'<h2 id="{slug}">{text}</h2>'

    return re.sub(r"<h2>([^<]+)</h2>", _slugify, html)


def _render_html(md_text: str) -> str:
    """Convert Markdown text to a complete HTML document string."""
    body = _markdown.markdown(md_text, extensions=["nl2br"])
    body = _add_heading_ids(body)
    photo_url = _photo_data_url()
    if photo_url:
        photo_tag = (
            '<div class="profile-photo-wrapper">'
            f'<img src="{photo_url}" class="profile-photo" alt="Profile photo">'
            "</div>"
        )
        body = photo_tag + body
    return _HTML_TEMPLATE.format(css=_CSS, body=body)


def _html_to_pdf(html: str) -> bytes:
    """Render an HTML string to PDF bytes via WeasyPrint."""
    return _HTML(string=html, base_url=None).write_pdf()


def markdown_to_pdf(md_text: str) -> bytes:
    """Convert a Markdown CV string to a styled PDF. Returns raw PDF bytes."""
    html = _render_html(md_text)
    return _html_to_pdf(html)
