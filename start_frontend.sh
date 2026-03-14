#!/bin/bash
# Quick start script for frontend

echo "🚀 Starting React Frontend..."
echo "=============================="

cd "$(dirname "$0")/frontend"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Start development server
echo "🌐 Starting frontend on http://localhost:3000"
echo ""
npm run dev

