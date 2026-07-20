"""
Stress test for the lexical/topical retrieval gates, reusing the methodology
from the _EMBED_RESCUE_THRESHOLD stress test (rag_pipeline.py:68-73): mix
paraphrase/vocabulary-mismatch queries against known-relevant docs (SHOULD
PASS) with genuinely off-topic queries (SHOULD FAIL), then check where each
gate's actual threshold agrees or disagrees with the expected label.

Scope: only gates whose formula is reachable without a live embedding call
(no Bedrock/Titan credentials in this environment) are exercised here —
topical_match_score() and significant_terms() are pure-lexical, so gates #4,
#9, #12 (which key off those) can be driven directly. Gates #5, #6, #7, #8
depend on the real vector-similarity `score` field (Titan embeddings via
Bedrock) and could not be stress-tested in this pass; flagged as a gap below.
"""

import sys
sys.path.insert(0, ".")

from backend.core.topical_relevance import (
    significant_terms,
    topical_match_score,
    _MIN_SIGNIFICANT_FOR_URL_CHECK,
)

def doc(title, url, product, content, score=0.5):
    return {
        "content": content,
        "score": score,
        "metadata": {"title": title, "url": url, "product": product},
    }


# (query, doc, expected_pass, note)
CASES = [
    # --- paraphrase / vocabulary-mismatch, SHOULD PASS (generic title, on-topic body) ---
    (
        "What are different kind of audiences like Batch, Streaming and Edge? explain in detail",
        doc(
            "Audience evaluation methods",
            "https://experienceleague.adobe.com/en/docs/experience-platform/segmentation/methods/overview",
            "Adobe Experience Platform",
            "Streaming segmentation is a segmentation evaluation method that you can use to evaluate "
            "audiences in near real-time. Batch segmentation runs on a fixed schedule. Edge segmentation "
            "evaluates audiences directly on the Edge Network.",
        ),
        True,
        "the original bug case — generic title/URL, on-topic body",
    ),
    (
        "How do RTCDP data limits work, like max profiles or dataset size?",
        doc(
            "Real-Time CDP Guardrails",
            "https://experienceleague.adobe.com/en/docs/experience-platform/rtcdp/guardrails/overview",
            "Adobe Experience Platform",
            "Guardrails define maximum limits for datasets, profiles, and segments in Real-Time CDP.",
        ),
        True,
        "'data limits' paraphrase of 'guardrails' — vocabulary mismatch",
    ),
    (
        "What's the difference between the ways Adobe evaluates audiences over time vs instantly?",
        doc(
            "Audience evaluation methods",
            "https://experienceleague.adobe.com/en/docs/experience-platform/segmentation/methods/overview",
            "Adobe Experience Platform",
            "Streaming segmentation evaluates audiences in near real-time. Batch segmentation evaluates "
            "on a schedule. Edge segmentation evaluates directly on the Edge Network.",
        ),
        True,
        "heavy paraphrase, zero literal term overlap with title/url",
    ),
    (
        "I'm new to CJA, how do I set it up step by step?",
        doc(
            "Introduction to Customer Journey Analytics",
            "https://experienceleague.adobe.com/en/docs/customer-journey-analytics/introduction",
            "Customer Journey Analytics",
            "Customer Journey Analytics (CJA) lets you combine data from multiple sources. Get started "
            "by creating a connection, then a data view.",
        ),
        True,
        "known-good case from the CJA onboarding fix (63d3220)",
    ),
    # --- genuinely off-topic, SHOULD FAIL ---
    (
        "What are the different ingestion guardrails for Adobe Experience Platform?",
        doc(
            "General Accessibility Features in Experience Platform",
            "https://experienceleague.adobe.com/en/docs/experience-platform/accessibility/features",
            "Adobe Experience Platform",
            "Users with disabilities frequently rely on assistive technologies.",
        ),
        False,
        "existing regression test case — wrong subtopic, same product",
    ),
    (
        "What are the different ingestion guardrails for Adobe Experience Platform?",
        doc(
            "Journey Optimizer Get Started for Data Engineer",
            "",
            "Adobe Journey Optimizer",
            "Configure source connectors. Adobe Journey Optimizer allows data to be ingested from "
            "external sources.",
        ),
        False,
        "existing regression test case — wrong product, superficial term overlap",
    ),
    (
        "How do I bake sourdough bread at home?",
        doc(
            "Audience evaluation methods",
            "https://experienceleague.adobe.com/en/docs/experience-platform/segmentation/methods/overview",
            "Adobe Experience Platform",
            "Streaming segmentation evaluates audiences in near real-time.",
        ),
        False,
        "control: fully unrelated query against a real doc",
    ),
    (
        "What license types does Adobe Target support?",
        doc(
            "Real-Time CDP Guardrails",
            "https://experienceleague.adobe.com/en/docs/experience-platform/rtcdp/guardrails/overview",
            "Adobe Experience Platform",
            "Guardrails define maximum limits for datasets, profiles, and segments in Real-Time CDP.",
        ),
        False,
        "cross-product mismatch — Target query against AEP guardrails doc",
    ),
]

_RAG_PIPELINE_WEAK_ALIGNMENT_THRESHOLD = 0.22  # gate #4, rag_pipeline.py:443
_NEIGHBOR_FILTER_OVERLAP = 0.08                # gate #9, retrieval_refiner.py:214
_NEIGHBOR_FILTER_SCORE = 0.12                  # gate #9, retrieval_refiner.py:214


def run():
    print(f"{'expect':<7} {'topical':<8} {'gate4_ok':<9} {'sig_terms':<10} note")
    mismatches = []
    for query, d, expect_pass, note in CASES:
        score = topical_match_score(query, d)
        sig = significant_terms(query)
        # Gate #4 shape: fails (blocks) if best_topical < 0.22 (embed rescue not
        # modeled here — no live embedding score available offline).
        gate4_would_block = score < _RAG_PIPELINE_WEAK_ALIGNMENT_THRESHOLD
        actual_pass = score >= 0.20 and not gate4_would_block
        status = "OK" if actual_pass == expect_pass else "MISMATCH"
        if actual_pass != expect_pass:
            mismatches.append((query, d["metadata"]["title"], expect_pass, actual_pass, score, note))
        print(f"{str(expect_pass):<7} {score:<8.3f} {str(not gate4_would_block):<9} "
              f"{len(sig):<10} {note}  [{status}]")

    print()
    if mismatches:
        print(f"{len(mismatches)} MISMATCH(ES):")
        for q, title, exp, act, score, note in mismatches:
            print(f"  - query={q!r}\n    doc={title!r} score={score:.3f} expected_pass={exp} actual_pass={act}\n    ({note})")
    else:
        print("All cases matched expectations.")


if __name__ == "__main__":
    run()
