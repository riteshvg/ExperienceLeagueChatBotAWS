# Railway Deployment Fixes

## Issues Fixed

### 1. **FastAPI Static File Serving**
   - **Problem**: Backend wasn't serving the frontend build files
   - **Solution**: Updated `backend/app/main.py` to:
     - Mount `/assets` directory for Vite build output
     - Serve `index.html` for all non-API routes (SPA routing)
     - Gracefully handle missing frontend build

### 2. **Start Script Simplification**
   - **Problem**: Complex start script with background processes and error handling issues
   - **Solution**: Simplified `start.sh` to:
     - Use Railway's `PORT` environment variable
     - Run uvicorn in foreground (Railway expects this)
     - Remove unnecessary dependency installation (handled by build phase)
     - Better error messages

### 3. **Build Configuration**
   - **Problem**: Railway/Nixpacks needed explicit build instructions for Python + Node.js project
   - **Solution**: Created `nixpacks.toml` to:
     - Install Python 3.11 and Node.js 18
     - Install backend dependencies
     - Install frontend dependencies
     - Build frontend
     - Set start command

### 4. **CORS Configuration**
   - **Problem**: CORS might block requests in production
   - **Solution**: Updated CORS to allow all origins in Railway environment (frontend served from same domain anyway)

## File Changes

1. **`backend/app/main.py`**
   - Added static file serving for frontend
   - Added SPA routing support

2. **`start.sh`**
   - Simplified to single uvicorn command
   - Uses Railway's PORT variable
   - Better error handling

3. **`backend/app/core/config.py`**
   - Updated CORS to be production-aware

4. **`nixpacks.toml`** (NEW)
   - Explicit build configuration for Railway

## Testing

To test locally before deploying:

```bash
# Build frontend
cd frontend
npm install
npm run build
cd ..

# Start backend (will serve frontend)
cd backend
source ../venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then visit:
- Frontend: http://localhost:8000
- API: http://localhost:8000/api/v1/health

## Railway Deployment

1. Push changes to GitHub
2. Railway will automatically:
   - Detect `nixpacks.toml`
   - Install Python and Node.js
   - Install dependencies
   - Build frontend
   - Run `start.sh`
   - Health check at `/api/v1/health`

## Health Check

The health check endpoint is at `/api/v1/health` and should return:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "..."
}
```

If health check fails:
1. Check Railway logs for startup errors
2. Verify environment variables are set
3. Check that frontend build completed successfully
4. Verify PORT environment variable is set by Railway

