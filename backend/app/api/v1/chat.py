"""
Chat API endpoints for query processing
"""
import sys
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from typing import Optional
import json
import asyncio
from fastapi import Query

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    ChatStreamChunk,
    QueryValidationRequest,
    QueryValidationResponse,
    SourceLink
)
from app.core.dependencies import get_settings, verify_aws_connection
from app.services.chat_service import ChatService

router = APIRouter()

# Global chat service instance (shared across requests for cache/session persistence)
_chat_service_instance: Optional[ChatService] = None

def get_chat_service(
    aws_info: dict = Depends(verify_aws_connection),
    settings = Depends(get_settings)
) -> ChatService:
    """Dependency to get chat service (singleton for cache/session persistence)"""
    global _chat_service_instance
    if _chat_service_instance is None:
        _chat_service_instance = ChatService(aws_info["clients"], settings)
    return _chat_service_instance


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Process a chat query and return response
    """
    try:
        result = chat_service.process_query(
            query=request.query,
            user_id=request.user_id,
            session_id=request.session_id
        )
        
        # Convert source links to SourceLink objects
        source_links = [
            SourceLink(
                title=link["title"],
                url=link["url"],
                video_url=link.get("video_url")
            )
            for link in result.get("source_links", [])
        ]
        
        return ChatResponse(
            success=result["success"],
            answer=result.get("answer"),
            error=result.get("error"),
            documents=result.get("documents", []),
            model_used=result.get("model_used"),
            routing_decision=result.get("routing_decision"),
            processing_time=result.get("processing_time"),
            source_links=source_links
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@router.post("/chat/validate", response_model=QueryValidationResponse)
async def validate_query(
    request: QueryValidationRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Validate a query before processing
    """
    validation = chat_service.validate_query(request.query)
    return QueryValidationResponse(**validation)


@router.websocket("/chat/stream")
async def chat_stream(websocket: WebSocket):
    """
    WebSocket endpoint for streaming chat responses
    """
    await websocket.accept()
    
    try:
        # Get settings and AWS clients
        settings = get_settings()
        aws_info = verify_aws_connection()
        chat_service = ChatService(aws_info["clients"], settings)
        
        # Receive query from client
        data = await websocket.receive_text()
        message = json.loads(data)
        query = message.get("query", "")
        user_id = message.get("user_id", "anonymous")
        session_id = message.get("session_id")
        
        if not query:
            await websocket.send_json({
                "success": False,
                "error": "Query is required",
                "chunk": "",
                "is_complete": True
            })
            await websocket.close()
            return
        
        # Process query with streaming
        async for chunk_data in chat_service.process_query_stream(
            query=query,
            user_id=user_id,
            session_id=session_id
        ):
            await websocket.send_json({
                "chunk": chunk_data.get("chunk", ""),
                "is_complete": chunk_data.get("is_complete", False),
                "success": chunk_data.get("success", True),
                "error": chunk_data.get("error"),
                "model_used": chunk_data.get("model_used"),
                "documents": chunk_data.get("documents", []),
                "source_links": chunk_data.get("source_links", [])
            })
            
            if chunk_data.get("is_complete"):
                break
        
        await websocket.close()
        
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({
                "success": False,
                "error": f"Error: {str(e)}",
                "chunk": "",
                "is_complete": True
            })
            await websocket.close()
        except:
            pass

