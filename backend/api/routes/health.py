"""Health check endpoint."""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    retriever = request.app.state.retriever
    return {
        "status": "ok",
        "chromadb": {
            "document_count": retriever.document_count(),
        },
    }
