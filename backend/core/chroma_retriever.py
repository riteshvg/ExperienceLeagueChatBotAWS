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

logger = logging.getLogger(__name__)

_DEFAULT_PERSIST_DIR = str(Path(__file__).parent.parent.parent / "chroma_db")
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
    def __init__(self, persist_dir: str = _DEFAULT_PERSIST_DIR):
        logger.info(f"Initialising ChromaDB at {persist_dir}")
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        region = os.getenv("BEDROCK_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
        self.bedrock = boto3.client("bedrock-runtime", region_name=region)
        logger.info(f"Using Titan Embed v2 for embeddings (region: {region})")

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

    def document_count(self) -> int:
        return self.collection.count()

    def collection_stats(self) -> dict:
        return {
            "collection": COLLECTION_NAME,
            "document_count": self.collection.count(),
            "embedding_model": TITAN_MODEL_ID,
        }
