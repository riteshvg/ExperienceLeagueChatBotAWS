#!/bin/bash

# Railway deployment script for Experience League Chatbot
# This script starts the FastAPI backend which serves both API and frontend
# IMPORTANT: This overrides any Streamlit auto-detection by Railway/Nixpacks

set -e  # Exit on error

echo "=========================================="
echo "🚀 Starting Experience League Chatbot on Railway..."
echo "📋 This is the FastAPI backend (NOT Streamlit)"
echo "=========================================="

# CRITICAL: Verify we're NOT running Streamlit
if command -v streamlit &> /dev/null; then
    echo "⚠️  WARNING: Streamlit is installed but we're using FastAPI"
    echo "⚠️  This should NOT trigger Streamlit auto-detection"
fi

# Verify we're in the right directory and using FastAPI
echo "✅ Verifying FastAPI setup..."
if [ ! -f "backend/app/main.py" ]; then
    echo "❌ ERROR: FastAPI app not found at backend/app/main.py"
    exit 1
fi

# Check if this is accidentally trying to run Streamlit
if [ -f "app_streamlit.py" ] && [ ! -f "app.py" ]; then
    echo "✅ Confirmed: app.py renamed to app_streamlit.py (Streamlit disabled)"
fi

# Get the port from Railway (defaults to 8000 if not set)
PORT=${PORT:-8000}
echo "📡 Using port: $PORT"

# Verify backend directory exists
if [ ! -d "backend" ]; then
    echo "❌ Error: backend directory not found"
    echo "Current directory: $(pwd)"
    echo "Contents: $(ls -la)"
    exit 1
fi

# Change to backend directory
cd backend || {
    echo "❌ Error: Cannot change to backend directory"
    exit 1
}

# Verify FastAPI app exists
if [ ! -f "app/main.py" ]; then
    echo "❌ Error: app/main.py not found"
    echo "Current directory: $(pwd)"
    echo "Contents: $(ls -la)"
    exit 1
fi

# Activate virtual environment if it exists (created during build)
if [ -d "venv" ]; then
    echo "✅ Activating virtual environment..."
    source venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️  Warning: Virtual environment not found, using system Python"
fi

# Start FastAPI with uvicorn
# Use 0.0.0.0 to bind to all interfaces (required for Railway)
# The backend will serve both API endpoints and static frontend files
echo "🔧 Starting FastAPI backend..."
echo "   - Host: 0.0.0.0"
echo "   - Port: $PORT"
echo "   - API: http://0.0.0.0:$PORT/api/v1"
echo "   - Health: http://0.0.0.0:$PORT/api/v1/health"
echo "   - Docs: http://0.0.0.0:$PORT/api/docs"

# Verify uvicorn is installed
if ! python -c "import uvicorn" 2>/dev/null; then
    echo "❌ Error: uvicorn not installed"
    echo "Installing uvicorn..."
    pip install uvicorn[standard]
fi

# Run uvicorn in the foreground (Railway expects the process to stay running)
# Use exec to replace shell process with uvicorn
echo "🚀 Starting uvicorn server..."
echo "   Command: python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT"
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
