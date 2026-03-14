"""
FastAPI main application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import (
    PROJECT_NAME,
    VERSION,
    API_V1_PREFIX,
    CORS_ORIGINS
)
from app.api.v1 import health, chat

# Create FastAPI app
app = FastAPI(
    title=PROJECT_NAME,
    version=VERSION,
    description="Backend API for Adobe Experience League Chatbot",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix=API_V1_PREFIX, tags=["health"])
app.include_router(chat.router, prefix=API_V1_PREFIX, tags=["chat"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Adobe Experience League Chatbot API",
        "version": VERSION,
        "docs": "/api/docs"
    }

