"""
ChromaDB-backed retriever replacing AWS Bedrock Knowledge Base retrieval.

Returns documents in the same shape the rest of the pipeline expects:
  [{"content": str, "location": {"s3Location": {"uri": str}}, "score": float}]
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Default persist directory relative to project root
_DEFAULT_PERSIST_DIR = str(Path(__file__).parent.parent.parent / "chroma_db")

COLLECTION_NAME = "experience_league"


class ChromaRetriever:
    def __init__(self, persist_dir: str = _DEFAULT_PERSIST_DIR):
        logger.info(f"Initialising ChromaDB at {persist_dir}")
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info("Loading sentence-transformer model (all-MiniLM-L6-v2)…")
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
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
    ) -> list[dict]:
        """
        Embed *query* and return the top-n_results matching chunks.

        Returns the same shape as Bedrock KB retrieve:
          [{"content": str, "location": {"s3Location": {"uri": str}}, "score": float}]
        """
        count = self.collection.count()
        if count == 0:
            logger.warning("ChromaDB collection is empty — no documents ingested yet")
            return []

        n = min(n_results, count)
        embedding = self.embedder.encode(query, show_progress_bar=False).tolist()

        kwargs: dict = dict(
            query_embeddings=[embedding],
            n_results=n,
            include=["documents", "metadatas", "distances"],
        )
        if where:
            kwargs["where"] = where

        results = self.collection.query(**kwargs)

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        output = []
        for doc, meta, dist in zip(docs, metas, dists):
            score = 1.0 - dist  # cosine distance → similarity
            if score < similarity_threshold:
                continue
            output.append(
                {
                    "content": doc,
                    "location": {
                        "s3Location": {"uri": meta.get("s3_key", "")}
                    },
                    "score": score,
                    "metadata": meta,
                }
            )

        return output

    def document_count(self) -> int:
        return self.collection.count()

    def collection_stats(self) -> dict:
        return {
            "collection": COLLECTION_NAME,
            "document_count": self.collection.count(),
            "persist_dir": str(self.client._settings.persist_directory
                               if hasattr(self.client, "_settings") else "unknown"),
        }
