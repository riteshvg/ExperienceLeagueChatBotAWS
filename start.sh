#!/bin/bash

# Railway deployment script for Experience League Chatbot
# This script starts both backend and frontend services

set -e

echo "🚀 Starting Experience League Chatbot on Railway..."

# Check if we're in production (Railway sets RAILWAY_ENVIRONMENT)
if [ -n "$RAILWAY_ENVIRONMENT" ]; then
    echo "📦 Production environment detected"
    
    # Install backend dependencies
    echo "📦 Installing backend dependencies..."
    cd backend
    pip install --upgrade pip
    pip install -r requirements.txt
    cd ..
    
    # Install frontend dependencies and build
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm install
    echo "🔨 Building frontend..."
    npm run build
    cd ..
    
    # Start backend in background
    echo "🔧 Starting FastAPI backend..."
    cd backend
    uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} &
    BACKEND_PID=$!
    cd ..
    
    # Wait for backend to be ready
    echo "⏳ Waiting for backend to be ready..."
    sleep 5
    
    # Start frontend server (serves built files)
    echo "🌐 Starting frontend server..."
    cd frontend
    npx serve -s dist -l ${PORT:-3000} &
    FRONTEND_PID=$!
    cd ..
    
    echo "✅ Services started!"
    echo "   Backend PID: $BACKEND_PID"
    echo "   Frontend PID: $FRONTEND_PID"
    
    # Wait for both processes
    wait $BACKEND_PID $FRONTEND_PID
else
    # Development mode - just start backend
    echo "🔧 Development mode - starting backend only..."
    cd backend
    uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
fi
