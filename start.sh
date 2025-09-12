#!/bin/bash
# Railway startup script for Streamlit app

# Set environment variables for Streamlit
export STREAMLIT_SERVER_PORT=${PORT:-8501}
export STREAMLIT_SERVER_ADDRESS=0.0.0.0
export STREAMLIT_SERVER_HEADLESS=true
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Set Railway database credentials
export RAILWAY_DATABASE_USER=postgres
export RAILWAY_DATABASE_PASSWORD=eeEcTALmHMkWxbKGKIEHRnMmYSEjbTDE

# Run Railway startup script (creates tables and starts app)
echo "🚀 Starting Railway application..."
python railway_startup.py
