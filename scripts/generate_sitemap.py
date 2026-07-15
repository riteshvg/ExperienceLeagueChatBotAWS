"""Generate frontend/public/sitemap.xml from every published /q/<slug> landing page.

Run before `npm run build` so Vite copies the fresh sitemap into dist/ (deploy.sh does this).

Usage:
    venv/bin/python scripts/generate_sitemap.py
"""

import sys
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env", override=False)

from backend.core import google_db  # noqa: E402

SITE_BASE = "https://thelearningproject.in/tools/rovr"
OUTPUT_PATH = Path(__file__).parent.parent / "frontend" / "public" / "sitemap.xml"


def main() -> None:
    slugs = google_db.list_published_slugs()

    urls = [f"{SITE_BASE}/"] + [f"{SITE_BASE}/q/{s['slug']}" for s in slugs]
    lastmods = {f"{SITE_BASE}/q/{s['slug']}": s["created_at"][:10] for s in slugs if s.get("created_at")}

    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{escape(url)}</loc>")
        if url in lastmods:
            lines.append(f"    <lastmod>{lastmods[url]}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")

    OUTPUT_PATH.write_text("\n".join(lines) + "\n")
    print(f"Wrote {len(urls)} URLs ({len(slugs)} published questions) → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
