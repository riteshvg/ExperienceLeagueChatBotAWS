"""
ChromaDB-backed retriever using Amazon Titan Embed Text v2 for embeddings.

Returns documents in the same shape the rest of the pipeline expects:
  [{"content": str, "location": {"s3Location": {"uri": str}}, "score": float}]
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import boto3
import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.core.chroma_paths import chroma_persist_dir

logger = logging.getLogger(__name__)

_DEFAULT_PERSIST_DIR = str(chroma_persist_dir())
COLLECTION_NAME = "experience_league"
TITAN_MODEL_ID = "amazon.titan-embed-text-v2:0"


def _get_titan_embedding(text: str, bedrock_client) -> list[float]:
    """Embed text using Amazon Titan Embed Text v2."""
    body = json.dumps({"inputText": text, "dimensions": 1024, "normalize": True})
    resp = bedrock_client.invoke_model(
        modelId=TITAN_MODEL_ID,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    return json.loads(resp["body"].read())["embedding"]


class ChromaRetriever:
    def __init__(self, persist_dir: str | None = None):
        persist_dir = persist_dir or str(chroma_persist_dir())
        logger.info(f"Initialising ChromaDB at {persist_dir}")
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        region = os.getenv("BEDROCK_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
        self.bedrock = boto3.client("bedrock-runtime", region_name=region)
        logger.info(f"Using Titan Embed v2 for embeddings (region: {region})")

        try:
            self.collection = self.client.get_collection(name=COLLECTION_NAME)
        except Exception as exc:
            logger.warning("get_collection failed (%s) — trying get_or_create", exc)
            self.collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        count = self.collection.count()
        logger.info(f"ChromaDB ready — {count} document chunks indexed")

    def retrieve(
        self,
        query: str,
        n_results: int = 8,
        similarity_threshold: float = 0.0,
        where: Optional[dict] = None,
        *,
        where_document: Optional[dict] = None,
    ) -> list[dict]:
        count = self.collection.count()
        if count == 0:
            logger.warning("ChromaDB collection is empty — no documents ingested yet")
            return []

        n = min(n_results, count)
        embedding = _get_titan_embedding(query, self.bedrock)

        kwargs: dict = dict(
            query_embeddings=[embedding],
            n_results=n,
            include=["documents", "metadatas", "distances"],
        )
        if where:
            kwargs["where"] = where
        if where_document:
            kwargs["where_document"] = where_document

        results = self.collection.query(**kwargs)

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        output = []
        for doc, meta, dist in zip(docs, metas, dists):
            score = 1.0 - dist
            if score < similarity_threshold:
                continue
            output.append({
                "content": doc,
                "location": {"s3Location": {"uri": meta.get("s3_key", "")}},
                "score": score,
                "metadata": meta,
            })

        return output

    def retrieve_document_contains(
        self,
        phrase: str,
        n_results: int = 8,
        similarity_threshold: float = 0.0,
        where: Optional[dict] = None,
    ) -> list[dict]:
        """Vector search restricted to chunks whose body contains ``phrase``."""
        needle = phrase.strip()
        if not needle:
            return []
        try:
            return self.retrieve(
                needle,
                n_results=n_results,
                similarity_threshold=similarity_threshold,
                where=where,
                where_document={"$contains": needle.lower()},
            )
        except Exception as exc:
            logger.debug("where_document contains failed for %r: %s", phrase[:40], exc)
            return []

    def document_count(self) -> int:
        return self.collection.count()

    def collection_stats(self) -> dict:
        return {
            "collection": COLLECTION_NAME,
            "document_count": self.collection.count(),
            "embedding_model": TITAN_MODEL_ID,
        }

    def product_breakdown(self) -> list[dict]:
        """Return per-product chunk + unique-page counts, sorted by chunk count desc."""
        total = self.collection.count()
        if total == 0:
            return []

        metas = []
        offset = 0
        PAGE = 500
        while True:
            page = self.collection.get(include=["metadatas"], limit=PAGE, offset=offset)
            batch = page.get("metadatas", [])
            if not batch:
                break
            metas.extend(batch)
            offset += len(batch)
            if len(batch) < PAGE:
                break

        from collections import defaultdict
        chunks: dict[str, int] = defaultdict(int)
        pages: dict[str, set] = defaultdict(set)

        for m in metas:
            product = m.get("product") or "Unknown"
            url = m.get("url") or m.get("s3_key") or ""
            chunks[product] += 1
            if url:
                pages[product].add(url)

        breakdown = [
            {"product": p, "chunks": chunks[p], "pages": len(pages[p])}
            for p in chunks
        ]
        breakdown.sort(key=lambda x: x["chunks"], reverse=True)
        return breakdown
