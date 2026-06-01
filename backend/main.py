"""
FastAPI application entry point.

Run:  uvicorn backend.main:app --reload --port 8000
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── Project root on sys.path ─────────────────────────────────────────────────
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.api.routes.admin import router as admin_router
from backend.api.routes.chat import router as chat_router
from backend.api.routes.health import router as health_router
from backend.core.chroma_retriever import ChromaRetriever
from backend.core.rag_pipeline import RAGPipeline
from backend.core.session_store import SessionStore
from config.settings import get_settings


def _configure_langsmith() -> None:
    """Set LangSmith env vars from settings so LangChain picks them up automatically."""
    s = get_settings()
    if s.langchain_tracing_v2 and s.langchain_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = s.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = s.langchain_project
        os.environ["LANGCHAIN_ENDPOINT"] = s.langchain_endpoint
        logging.getLogger(__name__).info(
            f"LangSmith tracing enabled — project: {s.langchain_project}"
        )
    else:
        logging.getLogger(__name__).info("LangSmith tracing disabled (set LANGCHAIN_TRACING_V2=true + LANGCHAIN_API_KEY to enable)")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_langsmith()
    logger.info("Starting up — loading ChromaDB and models…")
    retriever = ChromaRetriever()
    session_store = SessionStore()
    pipeline = RAGPipeline(retriever=retriever, session_store=session_store)

    app.state.retriever = retriever
    app.state.session_store = session_store
    app.state.pipeline = pipeline

    logger.info("Startup complete")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Experience League Chatbot API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:4173",   # Vite preview
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(health_router, prefix="/api")
