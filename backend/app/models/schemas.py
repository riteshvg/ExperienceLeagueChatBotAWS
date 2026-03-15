"""
Pydantic schemas for API requests and responses
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: datetime


class ConfigStatusResponse(BaseModel):
    """Configuration status response"""
    aws_configured: bool
    knowledge_base_configured: bool
    database_configured: bool
    aws_account_id: Optional[str] = None
    knowledge_base_id: Optional[str] = None
    region: Optional[str] = None


class ChatRequest(BaseModel):
    """Chat query request"""
    query: str = Field(..., min_length=3, max_length=20000, description="User query")
    session_id: Optional[str] = Field(None, description="Session ID for chat history")
    user_id: Optional[str] = Field("anonymous", description="User ID")


class SourceLink(BaseModel):
    """Source link to Experience League article"""
    title: str
    url: str
    video_url: Optional[str] = Field(None, description="Optional video link associated with the article")


class ChatResponse(BaseModel):
    """Chat response"""
    success: bool
    answer: Optional[str] = None
    error: Optional[str] = None
    documents: List[Dict[str, Any]] = Field(default_factory=list)
    model_used: Optional[str] = None
    routing_decision: Optional[Dict[str, Any]] = None
    processing_time: Optional[float] = None
    query_id: Optional[str] = None
    source_links: List[SourceLink] = Field(default_factory=list, description="Links to Experience League articles")


class ChatStreamChunk(BaseModel):
    """Streaming chat response chunk"""
    chunk: str
    is_complete: bool = False
    model_used: Optional[str] = None
    documents: List[Dict[str, Any]] = Field(default_factory=list)


class Message(BaseModel):
    """Chat message"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class ChatHistoryResponse(BaseModel):
    """Chat history response"""
    messages: List[Message]
    session_id: str


class QueryValidationRequest(BaseModel):
    """Query validation request"""
    query: str = Field(..., min_length=1, max_length=20000)


class QueryValidationResponse(BaseModel):
    """Query validation response"""
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    relevance_score: Optional[float] = None
    is_relevant: bool = True

