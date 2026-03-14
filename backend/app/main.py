"""
FastAPI main application
"""
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

# Serve static files from frontend/dist in production
# This allows Railway to serve both API and frontend from a single service
frontend_dist_path = Path(__file__).parent.parent.parent.parent / "frontend" / "dist"

# Root endpoint - serves frontend if available, otherwise returns API info
@app.get("/")
async def root():
    """Root endpoint - serves frontend if available, otherwise returns API info"""
    if frontend_dist_path.exists():
        index_path = frontend_dist_path / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
    return {
        "message": "Adobe Experience League Chatbot API",
        "version": VERSION,
        "docs": "/api/docs"
    }

# Mount static files if frontend build exists
if frontend_dist_path.exists():
    # Mount assets directory (Vite outputs JS, CSS, etc. to dist/assets/)
    assets_path = frontend_dist_path / "assets"
    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")
    
    # Mount any other static directories that might exist
    for static_dir in ["static", "public"]:
        static_path = frontend_dist_path / static_dir
        if static_path.exists():
            app.mount(f"/{static_dir}", StaticFiles(directory=str(static_path)), name=static_dir)
    
    # Serve index.html for all non-API routes (SPA routing)
    # This must be registered LAST so it doesn't catch API routes
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """
        Serve frontend for all non-API routes.
        This enables React Router to handle client-side routing.
        """
        # Don't serve frontend for API routes
        if full_path.startswith("api/"):
            return {"error": "Not found"}
        
        # Don't serve frontend for asset routes (handled by mounts above)
        if full_path.startswith(("assets/", "static/", "public/")):
            return {"error": "Not found"}
        
        # Serve index.html for all other routes
        index_path = frontend_dist_path / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return {"error": "Frontend not found"}

