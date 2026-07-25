# Open issues

Snapshot of open GitHub issues as of 2026-07-25. Source of truth is GitHub —
regenerate with `gh issue list --repo riteshvg/ExperienceLeagueChatBotAWS --state open`
rather than trusting this file if it's gone stale.

- [#26](https://github.com/riteshvg/ExperienceLeagueChatBotAWS/issues/26) — `_extract_citations()` URL-dedup can silently keep a lower-scoring chunk if input isn't score-sorted first
- [#25](https://github.com/riteshvg/ExperienceLeagueChatBotAWS/issues/25) — `_EMBED_RESCUE_THRESHOLD = 0.35` justified only by an inline comment, no reproducible test
- [#24](https://github.com/riteshvg/ExperienceLeagueChatBotAWS/issues/24) — `retrieval_refiner.py` has no dedicated test file — RRF fusion, multi-hop, and refinement threshold untested
- [#23](https://github.com/riteshvg/ExperienceLeagueChatBotAWS/issues/23) — `retrieval_refiner.py::_lexical_overlap`: camelCase `+0.2` per-term bonus shares single-term-collision shape
- [#22](https://github.com/riteshvg/ExperienceLeagueChatBotAWS/issues/22) — `topical_relevance.py`: topic-phrase `+0.12` flat bonus shares single-term-collision shape
- [#19](https://github.com/riteshvg/ExperienceLeagueChatBotAWS/issues/19) — Stress-test retrieval gates #5-#8 (embedding-dependent) with live Bedrock/Titan scores
- [#12](https://github.com/riteshvg/ExperienceLeagueChatBotAWS/issues/12) — Sources, follow-ups, copy/download missing after reopening a past conversation tab

See also [RETRIEVAL_SCORING_PRINCIPLES.md](RETRIEVAL_SCORING_PRINCIPLES.md) for
the scoring-pattern context behind #22-#25.
