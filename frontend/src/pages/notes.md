For copying changes from this folder to thelearningproject folder

cp -r /Users/riteshg/Documents/Learnings/experienceleaguechatbot/frontend/dist/\* \
 /Users/riteshg/Documents/Learnings/tlp/tlp/static/tools/exlunofficialchatbot/

Then run the command in the thelearningproject folder
hugo
git add .
git commit -m "commit message"
git push origin main

this will trigger cloudflare pages

Citation Issues — Summary

What was broken

Issue 1: Citations disappeared entirely in production

- Root cause: data/metadata_registry.json (1,850 entries) is in .gitignore and was never uploaded to Railway. The pipeline's \_extract_citations function depended on this file to
  build citation URLs — without it, every citation was silently dropped.
- Fix: Rewrote \_extract_citations to read url, title, product directly from ChromaDB chunk metadata (stored at ingest time), removing the registry file dependency entirely.

Issue 2: All citation URLs were 404 in production

- Root cause: The original registry was built in 2025 by scraping every .md file in the GitHub repos. But Experience League only serves a subset of those files — legacy admin
  pages, deprecated report builder docs, old c--prefixed filenames, etc. were removed from the live site. Over 53% of the 1,611 unique URLs in ChromaDB (855 of them) genuinely
  return 404 on EL today.
- The url_validator had been filtering these correctly, but it ran on Railway — and Railway's IP range was getting blocked by Adobe's CDN, causing valid pages to also fail the
  check and be dropped. Removing the validator exposed all the dead links at once.
- Fix: Ran the URL validator locally (no IP blocking), blanked the url field for all 855 dead-link chunks directly in ChromaDB, re-uploaded to S3, redeployed Railway.

Issue 3: [N] markers and citation pills still showing incorrectly

- Even with valid URLs, the citation numbers in answers weren't matching the right source cards.
- Fix: Removed citations entirely for now — stripped the "cite inline as [1], [2]" instruction from both system prompts, removed injectCitationLinks() and the Sources pills from
  the frontend, added stripCitationMarkers() to clean any stray [N] text the LLM might still output.

Current state

- Answers are clean with no citation markers
- ChromaDB still has the validated URL metadata (756 live URLs) — citations can be re-enabled later with a reliable matching strategy
- The URL cleanup script (scripts/fix_citation_urls.py) can be re-run periodically to prune stale links as EL reorganizes
