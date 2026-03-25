"""
Convert a Markdown CV string to a professionally styled PDF (bytes).

Usage:
    from src.pdf_generator import markdown_to_pdf
    pdf_bytes = markdown_to_pdf(md_text)
"""

import base64
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
    line-height: 1.35;
    margin: 0;
    padding: 0;
}

/* ── Name / header ── */
h1 {
    font-size: 15pt;
    color: #1a1a2e;
    border-bottom: 2pt solid #1a1a2e;
    padding-bottom: 4pt;
    margin: 0 0 4pt 0;
    line-height: 1.2;
}

/* Contact line is the first <p> after h1 */
h1 + p {
    font-size: 9pt;
    color: #555555;
    margin: 0 0 10pt 0;
}

/* ── Profile photo (floated top-right of header) ── */
.profile-photo-wrapper {
    float: right;
    margin: 0 0 6pt 12pt;
}

.profile-photo {
    width: 78pt;
    height: 78pt;
    border-radius: 50%;
    object-fit: cover;
    border: 1.5pt solid #1a1a2e;
    display: block;
}

/* ── Section headings ── */
h2 {
    clear: both;
    font-size: 10.5pt;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #1a1a2e;
    border-bottom: 0.75pt solid #cccccc;
    margin: 10pt 0 3pt 0;
    padding-bottom: 2pt;
    page-break-after: avoid;
}

/* ── Job title / sub-section headings ── */
h3 {
    font-size: 10pt;
    font-weight: bold;
    color: #1a1a2e;
    margin: 6pt 0 1pt 0;
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


def _render_html(md_text: str) -> str:
    """Convert Markdown text to a complete HTML document string."""
    body = _markdown.markdown(md_text, extensions=["nl2br"])
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
