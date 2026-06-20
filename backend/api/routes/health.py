"""Health check endpoint."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.core.knowledge_bank_status import build_health_payload

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    payload = build_health_payload(request.app)
    count = int((payload.get("chromadb") or {}).get("document_count") or 0)
    # Railway healthcheck: 503 only while index is empty; 200 once chunks are loaded.
    if payload.get("status") == "ok" or count > 0:
        status_code = 200
    else:
        status_code = 503
    return JSONResponse(content=payload, status_code=status_code)
