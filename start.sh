#!/bin/bash

# Railway deployment script for Experience League Chatbot
# This script starts the FastAPI backend which serves both API and frontend

echo "🚀 Starting Experience League Chatbot on Railway..."

# Get the port from Railway (defaults to 8000 if not set)
PORT=${PORT:-8000}
echo "📡 Using port: $PORT"

# Change to backend directory
cd backend || {
    echo "❌ Error: backend directory not found"
    exit 1
}

# Start FastAPI with uvicorn
# Use 0.0.0.0 to bind to all interfaces (required for Railway)
# The backend will serve both API endpoints and static frontend files
echo "🔧 Starting FastAPI backend..."
echo "   - Host: 0.0.0.0"
echo "   - Port: $PORT"
echo "   - API: http://0.0.0.0:$PORT/api/v1"
echo "   - Health: http://0.0.0.0:$PORT/api/v1/health"

# Run uvicorn in the foreground (Railway expects the process to stay running)
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
