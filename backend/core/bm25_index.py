"""
In-memory BM25 (sparse/lexical) index over the ingested chunk corpus.

ChromaDB has no native keyword/BM25 support — this builds a parallel
rank_bm25 index from the same collection's chunk text, so retrieval can
fuse dense (Titan embedding) and sparse (BM25) rankings via reciprocal
rank fusion. At ~8,500 chunks the whole index fits comfortably in memory
and (re)builds in well under a second.
"""

from __future__ import annotations

import logging
import re
import threading

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9._-]*")

_STOPWORDS = frozenset({
    "what", "how", "does", "the", "and", "for", "with", "via", "from", "that",
    "this", "are", "can", "you", "your", "about", "when", "where", "which",
    "into", "using", "use", "set", "get", "have", "has", "was", "were", "will",
    "should", "would", "could", "their", "they", "them", "then", "than", "also",
    "just", "only", "not", "but", "all", "any", "our", "its", "is", "a", "an",
    "to", "of", "in", "on", "at", "by", "or", "as", "be", "do", "i", "me",
    "my", "we", "if", "so", "up", "out", "no", "yes",
    # Procedural verbs that appear in nearly every how-to doc — carry no
    # topical signal for BM25's term-frequency weighting to key off, same
    # exclusion query_keywords._ACTION_TERMS applies to the heuristic pass.
    # Without this, "create"/"configure"/"steps" pollute rank for procedural
    # queries since they're common but not common enough for IDF alone to
    # zero them out over an ~8,500-chunk corpus.
    "implement", "install", "configure", "configuring", "configured", "setup",
    "create", "creating", "created", "enable", "add", "deploy", "walk",
    "steps", "step", "process", "full", "building", "built", "setting",
    "implementing", "implemented", "activating", "activate", "activated",
    "connecting", "connect", "connected", "integrating", "integrate",
    "integrated",
})

_PAGE_SIZE = 500


def tokenize(text: str) -> list[str]:
    """Lowercase word tokenizer shared by index build and query time."""
    return [
        t for t in _TOKEN_RE.findall((text or "").lower())
        if t not in _STOPWORDS and len(t) > 1
    ]


class BM25Index:
    """Lazily-built, thread-safe BM25 index over a Chroma collection's chunks."""

    def __init__(self):
        self._lock = threading.Lock()
        self._bm25: BM25Okapi | None = None
        self._ids: list[str] = []
        self._contents: list[str] = []
        self._metadatas: list[dict] = []
        self._built_for_count: int | None = None

    def ensure_built(self, retriever) -> None:
        """Build (or rebuild, if the collection size changed) the index."""
        count = retriever.collection.count()
        if self._bm25 is not None and self._built_for_count == count:
            return
        with self._lock:
            if self._bm25 is not None and self._built_for_count == count:
                return
            self._build(retriever, count)

    def _build(self, retriever, count: int) -> None:
        logger.info("Building BM25 index over %d chunks", count)
        ids: list[str] = []
        contents: list[str] = []
        metadatas: list[dict] = []
        offset = 0
        while True:
            page = retriever.collection.get(
                include=["documents", "metadatas"],
                limit=_PAGE_SIZE,
                offset=offset,
            )
            batch_ids = page.get("ids", [])
            batch_docs = page.get("documents", [])
            batch_metas = page.get("metadatas", [])
            if not batch_ids:
                break
            ids.extend(batch_ids)
            contents.extend(batch_docs)
            metadatas.extend(batch_metas)
            offset += len(batch_ids)
            if len(batch_ids) < _PAGE_SIZE:
                break

        tokenized_corpus = [tokenize(doc) for doc in contents]
        self._bm25 = BM25Okapi(tokenized_corpus) if tokenized_corpus else None
        self._ids = ids
        self._contents = contents
        self._metadatas = metadatas
        self._built_for_count = count
        logger.info("BM25 index built: %d documents", len(ids))

    def search(
        self,
        query: str,
        n_results: int = 30,
        where: dict | None = None,
    ) -> list[dict]:
        """
        Return docs shaped like ChromaRetriever.retrieve() output, ranked by
        BM25 score. `score` is min-max normalized to [0, 1] within this result
        set so it's comparable in shape to embedding cosine scores (callers
        doing RRF fusion use rank, not the raw magnitude, so this is cosmetic).
        """
        if self._bm25 is None or not self._ids:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)

        product_filter = None
        if where and "product" in where:
            eq = where["product"]
            product_filter = eq.get("$eq") if isinstance(eq, dict) else eq

        candidates = []
        for idx, score in enumerate(scores):
            if score <= 0:
                continue
            meta = self._metadatas[idx] or {}
            if product_filter and meta.get("product") != product_filter:
                continue
            candidates.append((idx, score))

        candidates.sort(key=lambda pair: pair[1], reverse=True)
        candidates = candidates[:n_results]
        if not candidates:
            return []

        max_score = candidates[0][1] or 1.0
        results = []
        for idx, score in candidates:
            meta = self._metadatas[idx] or {}
            results.append({
                "content": self._contents[idx],
                "location": {"s3Location": {"uri": meta.get("s3_key", "")}},
                "score": score / max_score,
                "metadata": meta,
            })
        return results


_index = BM25Index()


def bm25_search(retriever, query: str, n_results: int = 30, where: dict | None = None) -> list[dict]:
    """Module-level convenience: ensures the shared index is built, then searches."""
    _index.ensure_built(retriever)
    return _index.search(query, n_results=n_results, where=where)


def warm_bm25_index(retriever) -> None:
    """Eagerly build the shared BM25 index — call at app startup so the first
    real query doesn't pay the build cost (multiple seconds over ~40k+ chunks)."""
    _index.ensure_built(retriever)
