"""
FastAPI application entry point.

Run:  uvicorn backend.main:app --reload --port 8000
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ── Project root on sys.path ─────────────────────────────────────────────────
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Load .env into os.environ before any module reads os.getenv()
try:
    from dotenv import load_dotenv
    load_dotenv(_ROOT / ".env", override=False)
except ImportError:
    pass

from backend.api.routes.admin import router as admin_router
from backend.api.routes.auth import router as auth_router
from backend.api.routes.chat import router as chat_router
from backend.api.routes.health import router as health_router
from backend.api.routes.oauth import router as oauth_router
from backend.core.chroma_retriever import ChromaRetriever
from backend.core import user_db, google_db
from backend.core.rag_pipeline import RAGPipeline
from backend.core.session_store import SessionStore
from config.settings import get_settings

_CHROMA_S3_KEY = os.getenv("CHROMA_S3_KEY", "chroma_db/chroma_db.tar.gz")
_CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"
_COLLECTION = "experience_league"


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes")


def _chroma_chunk_count_at(chroma_path: Path | None = None) -> int:
    path = chroma_path or _CHROMA_DIR
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        client = chromadb.PersistentClient(
            path=str(path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        col = client.get_collection(_COLLECTION)
        return col.count()
    except Exception as exc:
        logger.warning("Could not read Chroma collection count at %s: %s", path, exc)
        return 0


def _chroma_chunk_count() -> int:
    return _chroma_chunk_count_at(_CHROMA_DIR)


def _clear_chroma_dir() -> None:
    import shutil

    if _CHROMA_DIR.exists():
        shutil.rmtree(_CHROMA_DIR)
        logger.info(f"Cleared local ChromaDB at {_CHROMA_DIR}")


def _fix_chroma_permissions(chroma_path: Path | None = None) -> None:
    """Ensure Chroma files are writable on Railway volumes."""
    import stat

    target = chroma_path or _CHROMA_DIR
    if not target.exists():
        return
    dir_mode = stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
    file_mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH
    for root, dirs, files in os.walk(target):
        os.chmod(root, dir_mode)
        for name in dirs:
            os.chmod(os.path.join(root, name), dir_mode)
        for name in files:
            os.chmod(os.path.join(root, name), file_mode)
    logger.info("ChromaDB file permissions updated at %s", target)


def _restore_chroma_from_s3() -> bool:
    """Download and extract chroma_db.tar.gz from S3 when empty or forced."""
    import shutil
    import tarfile
    import tempfile

    import boto3

    force = _env_truthy("FORCE_CHROMA_RESTORE")
    count = _chroma_chunk_count()

    if force:
        logger.warning(
            "FORCE_CHROMA_RESTORE is set — wiping local ChromaDB and restoring from S3"
        )
        _clear_chroma_dir()
        count = 0
    elif count > 0:
        logger.info(f"ChromaDB already populated ({count} chunks) — skipping S3 restore")
        return True

    bucket = os.getenv("AWS_S3_BUCKET", "")
    if not bucket:
        logger.warning("AWS_S3_BUCKET not set — skipping S3 restore")
        return False

    logger.info(f"ChromaDB empty — downloading from s3://{bucket}/{_CHROMA_S3_KEY} ...")
    restore_parent = Path(tempfile.mkdtemp(prefix="chroma_restore_"))
    tmp_archive: str | None = None
    try:
        s3 = boto3.client("s3", region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
            tmp_archive = tmp.name
        s3.download_file(bucket, _CHROMA_S3_KEY, tmp_archive)
        size_mb = Path(tmp_archive).stat().st_size / 1024 / 1024
        logger.info(f"Downloaded {size_mb:.1f} MB — extracting to staging dir ...")
        with tarfile.open(tmp_archive, "r:gz") as tar:
            tar.extractall(restore_parent)

        staged_dir = restore_parent / "chroma_db"
        if not staged_dir.exists():
            logger.error("Archive missing chroma_db/ directory after extract")
            return False

        _fix_chroma_permissions(staged_dir)
        restored = _chroma_chunk_count_at(staged_dir)
        if restored == 0:
            listing = list(staged_dir.rglob("*"))[:10]
            logger.error(
                "ChromaDB archive invalid — collection empty after staging extract; "
                f"sample files: {[str(p.relative_to(staged_dir)) for p in listing]}"
            )
            return False

        _CHROMA_DIR.parent.mkdir(parents=True, exist_ok=True)
        if _CHROMA_DIR.exists():
            shutil.rmtree(_CHROMA_DIR)
        shutil.copytree(staged_dir, _CHROMA_DIR)
        _fix_chroma_permissions(_CHROMA_DIR)

        logger.info(f"ChromaDB restored from S3 ✓ ({restored} chunks)")
        if force:
            logger.warning(
                "Unset FORCE_CHROMA_RESTORE on Railway after verifying /api/health "
                "so future deploys do not re-download on every restart"
            )
        return True
    except Exception as e:
        logger.warning(f"S3 restore failed: {e} — continuing with empty DB")
        return False
    finally:
        if tmp_archive:
            Path(tmp_archive).unlink(missing_ok=True)
        shutil.rmtree(restore_parent, ignore_errors=True)


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

    if _env_truthy("KNOWLEDGE_BANK_UPDATING") or _env_truthy("FORCE_CHROMA_RESTORE"):
        app.state.maintenance_started_at = datetime.now(timezone.utc)
        logger.info("Knowledge bank maintenance window started")

    # Initialise SQLite user DB (kept for demo counter + legacy compat)
    user_db.init_db()
    logger.info("SQLite user DB ready")

    # Initialise PostgreSQL Google OAuth tables
    try:
        google_db.init_tables()
        logger.info("Google OAuth DB tables ready (PostgreSQL)")
    except Exception as exc:
        logger.warning(
            f"Google OAuth DB init failed — Google sign-in will be unavailable: {exc}"
        )

    _restore_chroma_from_s3()
    _fix_chroma_permissions()
    try:
        retriever = ChromaRetriever()
    except Exception as e:
        logger.warning(f"ChromaDB init failed ({e}) — starting with empty retriever")
        retriever = None

    session_store = SessionStore()
    pipeline = RAGPipeline(retriever=retriever, session_store=session_store) if retriever else None

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

# Kill switch must be registered BEFORE CORSMiddleware.
# Starlette inserts each new middleware at the outermost position, so the last
# registration ends up outermost. Registering CORS last guarantees it wraps
# kill_switch and adds Access-Control-Allow-Origin to the 503 response.
@app.middleware("http")
async def kill_switch_middleware(request: Request, call_next):
    path = request.url.path
    # Only gate /api/* routes; let auth, admin, health, mcp, and OPTIONS through
    if (
        path.startswith("/api/")
        and not path.startswith("/api/auth/")
        and not path.startswith("/api/admin/")
        and not path.startswith("/api/health")
        and request.method != "OPTIONS"
    ):
        try:
            from backend.core.kill_switch import is_api_enabled
            if not is_api_enabled():
                return JSONResponse(
                    status_code=503,
                    content={"detail": "API_DISABLED"},
                )
        except Exception:
            pass

        try:
            from backend.core.knowledge_bank_status import (
                build_maintenance_payload,
                is_knowledge_bank_updating,
            )
            if is_knowledge_bank_updating(request.app):
                return JSONResponse(
                    status_code=503,
                    content=build_maintenance_payload(request.app),
                )
        except Exception:
            pass
    return await call_next(request)

# CORS registered last = outermost middleware = wraps everything including kill_switch
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:4173",   # Vite preview
        "http://localhost:3000",
        "https://thelearningproject.in",
        "https://www.thelearningproject.in",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(oauth_router)          # OAuth at root (/.well-known, /oauth/*)

# Mount MCP server for Claude.ai integration
from backend.mcp_server import get_mcp_asgi_app
app.mount("/mcp", get_mcp_asgi_app())
app.include_router(health_router, prefix="/api")
