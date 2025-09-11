#!/bin/bash
# Start Streamlit app with analytics enabled using SQLite

echo "🚀 Starting Adobe Analytics RAG Chatbot with Analytics..."
echo "📊 Analytics will be stored in SQLite database (analytics.db)"
echo ""

# Set environment variables for SQLite analytics
export USE_SQLITE=true
export SQLITE_DATABASE=analytics.db

# Start Streamlit
streamlit run app.py
