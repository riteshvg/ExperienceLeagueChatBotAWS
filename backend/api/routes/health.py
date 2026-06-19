"""Health check endpoint."""

from fastapi import APIRouter, Request

from backend.core.knowledge_bank_status import build_health_payload

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    return build_health_payload(request.app)
