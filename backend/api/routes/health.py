"""Health check endpoint."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.core.knowledge_bank_status import build_health_payload

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    payload = build_health_payload(request.app)
    # 503 while index is empty/updating so Railway healthcheck waits for restore.
    status_code = 200 if payload.get("status") == "ok" else 503
    return JSONResponse(content=payload, status_code=status_code)
