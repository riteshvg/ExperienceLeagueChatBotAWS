#!/bin/bash
# Railway startup script for Streamlit app

# Set environment variables for Streamlit
export STREAMLIT_SERVER_PORT=${PORT:-8501}
export STREAMLIT_SERVER_ADDRESS=0.0.0.0
export STREAMLIT_SERVER_HEADLESS=true
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Start Streamlit application
echo "🚀 Starting Streamlit application..."
streamlit run app.py
