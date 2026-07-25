"""
Live-Bedrock stress test for gates #5-#8 (the embedding-dependent gates
gate_stress_test.py explicitly could not exercise offline).

Reuses the same 8 paraphrase-vs-off-topic query cases from
eval/gate_stress_test.py, but drives them through the real ChromaRetriever
(live Titan embeddings + real ChromaDB) instead of synthetic docs, so the
`score` field reflects actual vector similarity.

Gates checked against the real top-1 embedding score:
  #5  RAGPipeline._is_off_topic       (rag_pipeline.py:752)      threshold 0.25
  #6  retrieval_refiner._OFF_TOPIC_THRESHOLD  (retrieval_refiner.py:26) 0.25
  #7  retrieval_refiner._REFINEMENT_MIN_SCORE (retrieval_refiner.py:27) 0.20
  #8  refinement acceptance gate (retrieval_refiner.py:546)
      embed_top >= 0.25 OR composite_top >= 0.22 (composite not modeled here,
      so this only checks the embed_top >= 0.25 branch)

This does NOT change any thresholds. It only reports whether the real scores
agree or disagree with the expected pass/fail label, watching specifically
for gate #2's failure signature: a genuinely relevant doc scoring just under
a hard cutoff because of generic title/wording.
"""

import json
import sys

sys.path.insert(0, ".")

from backend.core.chroma_retriever import ChromaRetriever
from backend.core.rag_pipeline import RAGPipeline

# (query, expected_pass, note) - trimmed from eval/gate_stress_test.py CASES;
# expected_pass here means "a real, on-topic doc should be retrievable",
# i.e. the off-topic gate should NOT fire.
QUERIES = [
    (
        "What are different kind of audiences like Batch, Streaming and Edge? explain in detail",
        True,
        "the original bug case — generic title/URL, on-topic body",
    ),
    (
        "How do RTCDP data limits work, like max profiles or dataset size?",
        True,
        "'data limits' paraphrase of 'guardrails' — vocabulary mismatch",
    ),
    (
        "What's the difference between the ways Adobe evaluates audiences over time vs instantly?",
        True,
        "heavy paraphrase, zero literal term overlap with title/url",
    ),
    (
        "I'm new to CJA, how do I set it up step by step?",
        True,
        "known-good case from the CJA onboarding fix (63d3220)",
    ),
    (
        "What are the different ingestion guardrails for Adobe Experience Platform?",
        False,
        "existing regression case — wrong subtopic, same product (accessibility doc)",
    ),
    (
        "How do I bake sourdough bread at home?",
        False,
        "control: fully unrelated query",
    ),
    (
        "What license types does Adobe Target support?",
        False,
        "cross-product mismatch — Target query, no Target license doc expected",
    ),
    (
        "orders calculated in AEP Web SDK",
        None,
        "issue #3 trigger query — recall/candidate-truncation suspect, included for cross-reference",
    ),
]

_OFF_TOPIC_THRESHOLD_5_6 = 0.25
_REFINEMENT_MIN_SCORE_7 = 0.20
_REFINEMENT_ACCEPT_8 = 0.25  # embed_top branch only; composite_top not modeled


def run():
    retriever = ChromaRetriever()
    results = []
    for query, expect_pass, note in QUERIES:
        docs = retriever.retrieve(query, n_results=8)
        top_score = max((d.get("score", 0.0) for d in docs), default=0.0)
        top_doc = docs[0] if docs else None
        top_title = (top_doc or {}).get("metadata", {}).get("title", "<none>")

        gate5_blocks = RAGPipeline._is_off_topic(docs, product_intent=None)
        gate6_triggers_refinement = top_score < _OFF_TOPIC_THRESHOLD_5_6
        gate7_floor_met = top_score >= _REFINEMENT_MIN_SCORE_7
        gate8_would_accept = top_score >= _REFINEMENT_ACCEPT_8

        near_miss = expect_pass is True and 0.20 <= top_score < 0.25
        row = {
            "query": query,
            "expect_pass": expect_pass,
            "note": note,
            "top_score": round(top_score, 4),
            "top_title": top_title,
            "gate5_blocks_as_off_topic": gate5_blocks,
            "gate6_would_trigger_refinement": gate6_triggers_refinement,
            "gate7_refinement_floor_met": gate7_floor_met,
            "gate8_would_accept_refined": gate8_would_accept,
            "near_miss_generic_title_signature": near_miss,
        }
        results.append(row)

        print(f"query: {query!r}")
        print(f"  expect_pass={expect_pass}  top_score={top_score:.4f}  top_title={top_title!r}")
        print(f"  gate5 blocks(off-topic)={gate5_blocks}  gate6 triggers_refine={gate6_triggers_refinement}"
              f"  gate7 floor_met={gate7_floor_met}  gate8 would_accept={gate8_would_accept}")
        if expect_pass is True and gate5_blocks:
            print("  *** MISMATCH: expected an on-topic answer but gate #5 would block it as off-topic ***")
        if expect_pass is False and not gate5_blocks:
            print("  *** MISMATCH: expected off-topic block but gate #5 would NOT block ***")
        if near_miss:
            print("  *** NEAR-MISS: on-topic query scoring in the 0.20-0.25 band — same shape as gate #2's failure ***")
        print(f"  note: {note}")
        print()

    with open("eval/live_gate_stress_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Wrote eval/live_gate_stress_results.json")


if __name__ == "__main__":
    run()
