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
from fastapi.responses import JSONResponse, RedirectResponse

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
from backend.core.chroma_paths import chroma_persist_dir
from backend.core.chroma_retriever import ChromaRetriever
from backend.core import user_db, google_db
from backend.core.rag_pipeline import RAGPipeline
from backend.core.session_store import SessionStore
from config.settings import get_settings

_CHROMA_S3_KEY = os.getenv("CHROMA_S3_KEY", "chroma_db/chroma_db.tar.gz")
_COLLECTION = "experience_league"
_RAILWAY_TMP_CHROMA = Path("/tmp/chroma_db")


def _refresh_chroma_dir() -> Path:
    """Resolve persist dir (honours Railway /tmp default) and sync module global."""
    global _CHROMA_DIR
    _CHROMA_DIR = chroma_persist_dir()
    os.environ["CHROMA_PERSIST_DIR"] = str(_CHROMA_DIR)
    return _CHROMA_DIR


def _set_chroma_dir(path: Path) -> None:
    global _CHROMA_DIR
    _CHROMA_DIR = path
    os.environ["CHROMA_PERSIST_DIR"] = str(path)


_CHROMA_DIR = _refresh_chroma_dir()

# Legacy Railway custom domain — browser traffic should land on the Hugo-hosted Rovr app.
_LEGACY_CHATBOT_HOSTS = frozenset({
    "chatbot.thelearningproject.in",
    "www.chatbot.thelearningproject.in",
})
_LEGACY_REDIRECT_SKIP_PREFIXES = (
    "/api/",
    "/mcp/",
    "/oauth/",
    "/.well-known/",
)


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


def _clear_chroma_dir_at(path: Path | None = None) -> None:
    """Remove Chroma files without deleting a Railway volume mount point."""
    import shutil

    target = path or _CHROMA_DIR
    if not target.exists():
        return
    for child in target.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    logger.info("Cleared ChromaDB contents at %s", target)


def _clear_chroma_dir() -> None:
    _clear_chroma_dir_at(_CHROMA_DIR)


def _remove_chroma_dest(dest: Path) -> None:
    """Remove destination tree safely (volume mount: contents only)."""
    import shutil

    if not dest.exists():
        return
    if dest == Path("/app/chroma_db"):
        _clear_chroma_dir_at(dest)
        return
    shutil.rmtree(dest)


def _install_chroma_tree(source: Path, dest: Path) -> tuple[bool, Path]:
    """Install a validated Chroma tree; return (ok, path actually used)."""
    import shutil

    if source.resolve() == dest.resolve():
        _fix_chroma_permissions(dest)
        count = _chroma_chunk_count_at(dest)
        logger.info("ChromaDB already at %s (%d chunks)", dest, count)
        return count > 0, dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    _remove_chroma_dest(dest)

    # Move, do not copy — shutil.copytree breaks Chroma SQLite on Railway.
    # dest must not exist or move nests source as dest/chroma_db/ (0 chunks).
    shutil.move(str(source), str(dest))
    _fix_chroma_permissions(dest)
    count = _chroma_chunk_count_at(dest)
    if count > 0:
        logger.info("Installed ChromaDB at %s (%d chunks)", dest, count)
        return True, dest

    # Files may exist but SQLite is unreadable on a Railway volume mount.
    if dest != _RAILWAY_TMP_CHROMA and dest.exists():
        logger.warning(
            "Chroma unreadable at %s after install — relocating tree to %s",
            dest,
            _RAILWAY_TMP_CHROMA,
        )
        _remove_chroma_dest(_RAILWAY_TMP_CHROMA)
        shutil.move(str(dest), str(_RAILWAY_TMP_CHROMA))
        _fix_chroma_permissions(_RAILWAY_TMP_CHROMA)
        count = _chroma_chunk_count_at(_RAILWAY_TMP_CHROMA)
        logger.info(
            "Installed ChromaDB at %s (%d chunks) after volume relocate",
            _RAILWAY_TMP_CHROMA,
            count,
        )
        if count > 0:
            return True, _RAILWAY_TMP_CHROMA

    logger.error("Install failed — 0 chunks at %s", dest)
    return False, dest


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

    if force:
        logger.warning(
            "FORCE_CHROMA_RESTORE is set — wiping local ChromaDB and restoring from S3"
        )
        _clear_chroma_dir()
    else:
        count = _chroma_chunk_count()
        if count > 0:
            logger.info(f"ChromaDB already populated ({count} chunks) — skipping S3 restore")
            return True
        if _CHROMA_DIR.exists():
            logger.warning(
                "ChromaDB path exists but collection count is 0 — clearing before S3 restore"
            )
            _clear_chroma_dir()

    bucket = os.getenv("AWS_S3_BUCKET", "")
    if not bucket:
        logger.warning("AWS_S3_BUCKET not set — skipping S3 restore")
        return False

    max_attempts = 2
    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            logger.warning("Chroma restore produced 0 chunks — retrying S3 download (attempt %d)", attempt)

        # Use a fresh temp dir — /tmp/chroma_db is unreliable on Railway (0 chunks after extract).
        data_parent = Path(tempfile.mkdtemp(prefix="chroma_data_", dir="/tmp"))
        tmp_archive: str | None = None
        try:
            logger.info(
                "ChromaDB empty — downloading from s3://%s/%s (attempt %d/%d) ...",
                bucket,
                _CHROMA_S3_KEY,
                attempt,
                max_attempts,
            )
            s3 = boto3.client("s3", region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
            with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
                tmp_archive = tmp.name
            s3.download_file(bucket, _CHROMA_S3_KEY, tmp_archive)
            size_mb = Path(tmp_archive).stat().st_size / 1024 / 1024
            logger.info("Downloaded %.1f MB — extracting to %s ...", size_mb, data_parent)

            with tarfile.open(tmp_archive, "r:gz") as tar:
                tar.extractall(data_parent)

            chroma_dir = data_parent / "chroma_db"
            if not chroma_dir.is_dir() or not (chroma_dir / "chroma.sqlite3").is_file():
                logger.error("Archive missing chroma_db/chroma.sqlite3 after extract")
                shutil.rmtree(data_parent, ignore_errors=True)
                continue

            sqlite_mb = (chroma_dir / "chroma.sqlite3").stat().st_size / 1024 / 1024
            logger.info(
                "Extracted ChromaDB archive OK (chroma.sqlite3 %.1f MB at %s)",
                sqlite_mb,
                chroma_dir,
            )

            _fix_chroma_permissions(chroma_dir)
            import gc
            gc.collect()

            count = _chroma_chunk_count_at(chroma_dir)
            if count <= 0:
                logger.error("Extract finished but collection count is still 0 at %s", chroma_dir)
                shutil.rmtree(data_parent, ignore_errors=True)
                continue

            _set_chroma_dir(chroma_dir)
            logger.info(
                "ChromaDB restored from S3 ✓ (%d chunks at %s)",
                count,
                chroma_dir,
            )
            if force:
                logger.warning(
                    "Unset FORCE_CHROMA_RESTORE on Railway after verifying /api/health "
                    "so future deploys do not re-download on every restart"
                )
            return True
        except Exception as e:
            logger.warning(f"S3 restore attempt {attempt} failed: {e}")
            shutil.rmtree(data_parent, ignore_errors=True)
        finally:
            if tmp_archive:
                Path(tmp_archive).unlink(missing_ok=True)

    return False


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
    persist = _refresh_chroma_dir()
    logger.info("Starting up — loading ChromaDB and models…")
    logger.info("Chroma persist directory: %s", persist)

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
    persist = chroma_persist_dir()
    _fix_chroma_permissions(persist)
    import gc
    gc.collect()
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


@app.middleware("http")
async def legacy_chatbot_host_redirect(request: Request, call_next):
    """Send legacy chatbot subdomain visitors to the Rovr SPA on the main site."""
    host = (request.headers.get("host") or "").split(":")[0].lower()
    if host not in _LEGACY_CHATBOT_HOSTS:
        return await call_next(request)
    path = request.url.path
    if any(path.startswith(prefix) for prefix in _LEGACY_REDIRECT_SKIP_PREFIXES):
        return await call_next(request)
    if request.method not in ("GET", "HEAD"):
        return await call_next(request)
    target = get_settings().frontend_url.rstrip("/") + "/"
    return RedirectResponse(url=target, status_code=301)


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
