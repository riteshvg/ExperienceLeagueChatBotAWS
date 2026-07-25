# Retrieval scoring principles

Two failure shapes have each caused a real doc to be mis-ranked or wrongly
blocked in this pipeline (`topical_relevance.py`, `query_keywords.py`,
`retrieval_refiner.py`). Both were found by beta testers before they were
found by review. Check new scoring/gating code against them before shipping.

## 1. Flat/binary bonus for "any match > 0"

A bonus that triggers on *any* match, worth the same whether 1 term hit or
all of them, rewards an incidental collision as much as a genuine one.

**Worked example — `topical_relevance.py`'s URL-hit bonus:**

```python
# Before: flat +0.15 no matter how many of the query's terms actually hit
if url_hits > 0:
    score = min(1.0, score + 0.15)

# After: scaled by the fraction of terms that hit
if url_ratio > 0:
    score = min(1.0, score + 0.15 * url_ratio)
```

The adversarial test that caught it: a query sharing exactly **one** real
(non-generic) term with a doc's URL slug — e.g. "How do I authenticate my
identity at passport control, unrelated to Analytics API" against a doc
titled `Analytics 2.0 API Authentication` (URL ends in `authenticate.html`).
Before the fix this scored `0.35` — same as several genuinely on-topic
paraphrases — purely from the flat bonus on one incidental hit. After
scaling by `url_ratio` (1 hit out of 5 query terms), it dropped to `0.23`,
clear of the genuine-match range.

Still open with this same shape (tracked, not yet fixed): the topic-phrase
`+0.12` bonus in `topical_relevance.py` and the camelCase `+0.2` per-term
bonus in `retrieval_refiner.py::_lexical_overlap` — see issues
[#22](https://github.com/riteshvg/ExperienceLeagueChatBotAWS/issues/22) and
[#23](https://github.com/riteshvg/ExperienceLeagueChatBotAWS/issues/23).

## 2. `hits / total` with a small denominator

A ratio computed from `hits / total` is only meaningful when `total` is
large enough that one hit or miss can't swing it to the extremes. With
`total == 1`, a single incidental match saturates the score to `1.0`
regardless of actual relevance.

**Worked example — `query_keywords.py`'s `hybrid_doc_score`:**

`keyword_match_score` computes `term_hits / term_total`. For the query
"segment setup steps", `match_terms == ["segment"]` (`term_total == 1`) — so
*any* doc containing the word "segment" scored `0.45` on this term, whether
it was genuinely about Real-Time CDP audience segmentation or an unrelated
Adobe Analytics segment-overview page. Same shape for "profile" and
"identity" as the sole surviving term.

The fix does **not** stopword-list these words the way the original
"Calculated Metrics" bug was fixed (by adding `"calculated"` to
`_ACTION_TERMS`). That doesn't generalize here: "calculated" is a generic
derivation verb with no topic signal in any context, but "segment",
"profile", and "identity" are genuine, load-bearing domain nouns — blanket-
excluding them would silence real topical signal for a large share of
CDP/Analytics/AEP queries, trading one failure mode for a worse one.

Instead, `hybrid_doc_score` dampens the keyword weight when `term_total` is
below a calibrated minimum (`_MIN_RELIABLE_TERM_TOTAL = 2`), shifting weight
toward the embedding score proportionally:

```python
if term_total < _MIN_RELIABLE_TERM_TOTAL:
    confidence = term_total / _MIN_RELIABLE_TERM_TOTAL
    embed_weight = embed_weight + (1.0 - embed_weight) * (1.0 - confidence)
```

The threshold (`2`) was chosen empirically, not picked as a round number:
tested against a collision suite (segment/profile/identity) *and* a harder
genuine case where the embedding score coincidentally favored the wrong
doc, across candidate values `{2, 3, 4, 5}`. `2` was the smallest value that
closed the collision without also erasing legitimate single-term rescue
signal — `3` and above already broke the genuine case. See
`tests/test_query_keywords.py::TestSingleTermCollisionDampening`.

## Checklist before shipping new scoring/gating logic here

- [ ] **Flat bonus or scaled?** Does this bonus grow with match strength/ratio,
      or does it fire the same way on 1 match as on 10?
- [ ] **Small denominator?** Can the ratio's `total` ever be 1 or 2 in
      practice? If so, what happens to a single incidental hit or miss?
- [ ] **Adversarial-tested, not just comment-tested?** Has this been run
      against real off-topic queries that could exploit the exact pattern
      above, with real computed scores — not just an inline comment
      asserting "verified" or "stress-tested"? (If the claim can't be
      re-run, it isn't verification.)

## Backlog of items still needing this treatment

- [#18](https://github.com/riteshvg/ExperienceLeagueChatBotAWS/issues/18) —
  pre-existing mock failures in `TestWeakTopicalAlignmentGate`
- [#19](https://github.com/riteshvg/ExperienceLeagueChatBotAWS/issues/19) —
  stress-test retrieval gates #5–#8 with live embedding scores
- [#22](https://github.com/riteshvg/ExperienceLeagueChatBotAWS/issues/22) —
  topic-phrase `+0.12` flat bonus (`topical_relevance.py`)
- [#23](https://github.com/riteshvg/ExperienceLeagueChatBotAWS/issues/23) —
  camelCase `+0.2` per-term bonus (`retrieval_refiner.py::_lexical_overlap`)
