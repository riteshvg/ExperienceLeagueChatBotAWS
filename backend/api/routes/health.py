"""Health check endpoint."""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    retriever = getattr(request.app.state, "retriever", None)
    return {
        "status": "ok",
        "chromadb": {
            "document_count": retriever.document_count() if retriever else 0,
        },
    }
