"""Generate a static, crawlable HTML file per published /q/<slug> landing page.

The SPA's index.html is the same for every route, so LinkedIn/Slack/Twitter link
scrapers (which don't execute JS) and most search crawlers see no page-specific
content when a /q/<slug> URL is shared or crawled. This writes a real
dist/q/<slug>/index.html per published question with:
  - <title>, meta description, and Open Graph/Twitter tags in <head>
  - the actual question + answer + source links rendered as plain HTML inside
    #root, so a crawler that never runs JS still sees real page content
  - FAQ JSON-LD structured data, making the page eligible for Google's
    FAQ rich-result snippets

The React app still boots from the same bundle and overwrites #root's children
normally once JS runs — no hydration, so no mismatch from the static content.

Must run after `npm run build` (needs frontend/dist/index.html as the template)
and before the dist/ directory is copied into the Hugo static tree, so the
generated files get picked up by that copy. deploy.sh wires this in.

Usage:
    venv/bin/python scripts/generate_landing_pages.py
"""

import json
import re
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env", override=False)

from backend.core import google_db  # noqa: E402

SITE_BASE = "https://thelearningproject.in/tools/rovr"
OG_IMAGE = f"{SITE_BASE}/rovrlogo.png"
DIST_DIR = Path(__file__).parent.parent / "frontend" / "dist"
TEMPLATE_PATH = DIST_DIR / "index.html"
DESCRIPTION_LEN = 160


def plain_text_snippet(markdown_answer: str, length: int) -> str:
    text = re.sub(r"[#*_`>\[\]]", "", markdown_answer or "")
    text = re.sub(r"\s+", " ", text).strip()
    return (text[: length - 1].rsplit(" ", 1)[0] + "…") if len(text) > length else text


def build_head_tags(query: str, description: str, url: str) -> str:
    title = escape(query)
    desc = escape(description)
    return "\n".join(
        [
            f"<title>{title} | Rovr</title>",
            f'<meta name="description" content="{desc}" />',
            f'<link rel="canonical" href="{url}" />',
            f'<meta property="og:title" content="{title}" />',
            f'<meta property="og:description" content="{desc}" />',
            f'<meta property="og:url" content="{url}" />',
            '<meta property="og:type" content="article" />',
            f'<meta property="og:image" content="{OG_IMAGE}" />',
            '<meta name="twitter:card" content="summary" />',
            f'<meta name="twitter:title" content="{title}" />',
            f'<meta name="twitter:description" content="{desc}" />',
        ]
    )


def markdown_to_html(markdown_text: str) -> str:
    """Minimal, dependency-free markdown → HTML good enough for crawler-visible static content."""
    text = escape(markdown_text or "")
    lines = text.split("\n")
    html_lines: list[str] = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        heading = re.match(r"^(#{1,6})\s+(.*)", stripped)
        bullet = re.match(r"^[-*]\s+(.*)", stripped)
        if bullet:
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{bullet.group(1)}</li>")
            continue
        if in_list:
            html_lines.append("</ul>")
            in_list = False
        if re.match(r"^-{3,}$", stripped):
            html_lines.append("<hr>")
        elif heading:
            level = min(len(heading.group(1)) + 1, 6)  # h1 reserved for the question
            html_lines.append(f"<h{level}>{heading.group(2)}</h{level}>")
        elif stripped:
            html_lines.append(f"<p>{stripped}</p>")
    if in_list:
        html_lines.append("</ul>")

    body = "\n".join(html_lines)
    body = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", body)
    body = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", body)
    body = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1">', body)
    body = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', body)
    return body


def build_sources_html(citations: list[dict]) -> str:
    if not citations:
        return ""
    items = "\n".join(
        f'<li><a href="{escape(c.get("url", ""))}">{escape(c.get("title") or c.get("url", ""))}</a></li>'
        for c in citations
        if c.get("url")
    )
    return f"<h2>Sources</h2>\n<ul>\n{items}\n</ul>" if items else ""


def build_faq_jsonld(query: str, answer_text: str, url: str) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": query,
                "acceptedAnswer": {"@type": "Answer", "text": plain_text_snippet(answer_text, 2000)},
            }
        ],
    }
    payload = json.dumps(data).replace("</script", "<\\/script")
    return f'<script type="application/ld+json">{payload}</script>'


def build_body_content(landing: dict, url: str) -> str:
    answer_html = markdown_to_html(landing["answer"])
    sources_html = build_sources_html(landing.get("citations") or [])
    jsonld = build_faq_jsonld(landing["query"], landing["answer"], url)
    return (
        f'<article><h1>{escape(landing["query"])}</h1>\n{answer_html}\n{sources_html}</article>\n{jsonld}'
    )


def render_page(template: str, landing: dict, description: str, url: str) -> str:
    page = re.sub(r"<title>.*?</title>", "", template, flags=re.DOTALL)
    page = re.sub(r'<meta\s+property="og:title"[^>]*/?>', "", page)
    page = page.replace("</head>", build_head_tags(landing["query"], description, url) + "\n</head>")
    return page.replace('<div id="root"></div>', f'<div id="root">{build_body_content(landing, url)}</div>')


def main() -> None:
    if not TEMPLATE_PATH.exists():
        raise SystemExit(f"{TEMPLATE_PATH} not found — run `npm run build` first.")
    template = TEMPLATE_PATH.read_text()

    slugs = google_db.list_published_slugs()
    written = 0
    for entry in slugs:
        slug = entry["slug"]
        landing = google_db.get_landing_by_slug(slug)
        if not landing:
            continue
        url = f"{SITE_BASE}/q/{slug}"
        description = plain_text_snippet(landing["answer"], DESCRIPTION_LEN)
        page = render_page(template, landing, description, url)

        out_dir = DIST_DIR / "q" / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(page)
        written += 1

    print(f"Wrote {written} landing pages → {DIST_DIR}/q/<slug>/index.html")


if __name__ == "__main__":
    main()
