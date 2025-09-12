#!/bin/bash
# Railway startup script for Streamlit app

# Set environment variables for Streamlit
export STREAMLIT_SERVER_PORT=${PORT:-8501}
export STREAMLIT_SERVER_ADDRESS=0.0.0.0
export STREAMLIT_SERVER_HEADLESS=true
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Initialize database if needed
echo "🔧 Initializing Railway database..."
python init_railway_db.py

# Check if database initialization was successful
if [ $? -eq 0 ]; then
    echo "✅ Railway database initialization completed successfully"
else
    echo "⚠️  Railway database initialization had issues, but continuing..."
fi

# Start Streamlit
echo "🚀 Starting Streamlit app..."
streamlit run app.py --server.port=$STREAMLIT_SERVER_PORT --server.address=$STREAMLIT_SERVER_ADDRESS --server.headless=true
