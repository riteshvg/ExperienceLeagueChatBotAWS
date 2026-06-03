"""
MCP Server — Experience League Documentation Search

Exposes the ChromaDB knowledge base as an MCP tool so developers can
query Adobe Experience League docs directly from Claude Code or any
MCP-compatible IDE.

Usage (local):
    python backend/mcp_server.py

Add to ~/.claude/settings.json:
    {
      "mcpServers": {
        "experience-league": {
          "command": "python",
          "args": ["/full/path/to/experienceleaguechatbot/backend/mcp_server.py"]
        }
      }
    }
"""

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

import os
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import TransportSecuritySettings
from backend.core.chroma_retriever import ChromaRetriever
from src.utils.citation_mapper import format_citation
from src.utils.query_processor import QueryProcessor

_RAILWAY_HOST = "experienceleaguechatbotaws-production.up.railway.app"

mcp = FastMCP(
    "experience-league-docs",
    transport_security=TransportSecuritySettings(
        allowed_hosts=[
            _RAILWAY_HOST,
            "localhost",
            "localhost:8000",
            "localhost:8080",
        ],
        allowed_origins=[
            f"https://{_RAILWAY_HOST}",
            "http://localhost:8000",
            "http://localhost:8080",
        ],
    ),
)

# Lazy init — populated on first call so importing this module doesn't
# trigger ChromaDB/Bedrock connections at import time (needed for ASGI mount)
_retriever = None
_query_processor = None


def _ensure_init():
    global _retriever, _query_processor
    if _retriever is None:
        _retriever = ChromaRetriever()
        _query_processor = QueryProcessor()


@mcp.tool()
def search_experience_league(query: str) -> str:
    """
    Search Adobe Experience League documentation.

    Use this tool to find information about Adobe Analytics, Customer Journey
    Analytics (CJA), and Adobe Experience Platform (AEP). Returns the most
    relevant documentation chunks with source URLs.

    Args:
        query: Natural language question or keyword search.
               Use specific Adobe terminology for best results.
    """
    _ensure_init()
    enhanced, _ = _query_processor.preprocess_query(query)
    docs = _retriever.retrieve(enhanced, n_results=5, similarity_threshold=0.2)

    if not docs:
        return f"No documentation found for: {query}"

    parts = []
    for i, doc in enumerate(docs, 1):
        meta = doc.get("metadata", {})
        citation = format_citation(doc, doc_title=meta.get("title"))
        url = citation.get("url", "")
        title = citation.get("title", f"Document {i}")
        product = citation.get("product", "")
        score = doc.get("score", 0)

        header = f"[{i}] {title}"
        if product:
            header += f" ({product})"
        if url:
            header += f"\nSource: {url}"
        header += f"\nRelevance: {score:.0%}"

        parts.append(f"{header}\n\n{doc['content'][:600]}...")

    return "\n\n---\n\n".join(parts)


@mcp.tool()
def get_product_overview(product: str) -> str:
    """
    Get an overview of an Adobe product's documentation coverage.

    Args:
        product: One of 'Adobe Analytics', 'Customer Journey Analytics',
                 'Adobe Experience Platform'
    """
    _ensure_init()
    docs = _retriever.retrieve(
        f"{product} overview introduction",
        n_results=3,
        similarity_threshold=0.2,
    )
    if not docs:
        return f"No overview found for: {product}"

    parts = []
    for doc in docs:
        meta = doc.get("metadata", {})
        if product.lower() in meta.get("product", "").lower():
            parts.append(doc["content"][:400])

    return "\n\n---\n\n".join(parts[:2]) if parts else f"No content found for {product}"


@mcp.tool()
def list_available_products() -> str:
    """List the Adobe products available in the knowledge base."""
    return (
        "The following Adobe products are indexed:\n"
        "- Adobe Analytics (964 pages)\n"
        "- Customer Journey Analytics / CJA (136 pages)\n"
        "- Adobe Experience Platform / AEP (160 pages)\n\n"
        "Knowledge base cutoff: March 14, 2026"
    )


def get_mcp_asgi_app():
    """Return the MCP SSE app for mounting in FastAPI at /mcp.

    Exposes:
      GET  /mcp/sse       — SSE stream (Claude.ai connects here)
      POST /mcp/messages/ — message endpoint
    """
    return mcp.sse_app()


if __name__ == "__main__":
    # Standalone mode: initialize and run via stdio (Claude Code)
    _ensure_init()
    mcp.run()
