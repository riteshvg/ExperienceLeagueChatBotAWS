#!/bin/bash
# Quick start script for backend

echo "🚀 Starting FastAPI Backend..."
echo "================================"

cd "$(dirname "$0")/backend"

# Activate virtual environment
if [ -d "../venv" ]; then
    source ../venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Virtual environment not found. Please create it first:"
    echo "   python3 -m venv venv"
    exit 1
fi

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Start server
echo "🌐 Starting server on http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/api/docs"
echo ""
uvicorn app.main:app --reload --port 8000

