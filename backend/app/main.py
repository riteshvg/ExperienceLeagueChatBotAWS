"""
FastAPI main application
"""
import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# CRITICAL: Add startup logging at the very top
print("=" * 60)
print("[STARTUP] FastAPI Application Starting...")
print("=" * 60)
print(f"[INFO] Python version: {sys.version.split()[0]}")
print(f"[INFO] Working directory: {os.getcwd()}")
print(f"[INFO] Environment: {os.getenv('ENVIRONMENT', 'development')}")
print("=" * 60)

try:
    from app.core.config import (
        PROJECT_NAME,
        VERSION,
        API_V1_PREFIX,
        CORS_ORIGINS
    )
    print(f"[OK] Configuration loaded: {PROJECT_NAME} v{VERSION}")
except Exception as e:
    print(f"[ERROR] Failed to load configuration: {e}")
    print("[WARN] Continuing with defaults...")
    PROJECT_NAME = "Adobe Experience League Chatbot API"
    VERSION = "1.0.0"
    API_V1_PREFIX = "/api/v1"
    CORS_ORIGINS = ["*"]

try:
    from app.api.v1 import health, chat
    print("[OK] API routers imported successfully")
except Exception as e:
    print(f"[ERROR] Failed to import API routers: {e}")
    import traceback
    traceback.print_exc()
    raise

# Create FastAPI app
print("[INFO] Creating FastAPI application...")
app = FastAPI(
    title=PROJECT_NAME,
    version=VERSION,
    description="Backend API for Adobe Experience League Chatbot",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)
print("[OK] FastAPI app created")

# Configure CORS
print("[INFO] Configuring CORS...")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
print(f"[OK] CORS configured with origins: {CORS_ORIGINS}")

# Include routers
print("[INFO] Registering API routers...")
app.include_router(health.router, prefix=API_V1_PREFIX, tags=["health"])
app.include_router(chat.router, prefix=API_V1_PREFIX, tags=["chat"])
print(f"[OK] Routers registered at {API_V1_PREFIX}")

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

# Startup event - log that app is ready
@app.on_event("startup")
async def startup_event():
    """Log application startup"""
    print("=" * 60)
    print("[OK] FastAPI Application Started Successfully!")
    print(f"[INFO] Health check available at: /api/v1/health")
    print(f"[INFO] API docs available at: /api/docs")
    print("=" * 60)

