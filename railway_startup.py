#!/usr/bin/env python3
"""
Railway startup script that creates tables and starts the Streamlit app.
This script runs on Railway deployment to ensure tables are created.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_table_creation():
    """Run the table creation script."""
    logger.info("🔧 Running table creation script...")
    
    try:
        # Import and run the table creation function directly
        from railway_table_creator import create_analytics_tables
        
        success = create_analytics_tables()
        
        if success:
            logger.info("✅ Table creation completed successfully")
            return True
        else:
            logger.error("❌ Table creation failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error running table creation: {e}")
        return False

def start_streamlit():
    """Start the Streamlit app."""
    logger.info("🚀 Starting Streamlit app...")
    
    try:
        # Set Streamlit environment variables
        os.environ.setdefault("STREAMLIT_SERVER_PORT", "8501")
        os.environ.setdefault("STREAMLIT_SERVER_ADDRESS", "0.0.0.0")
        os.environ.setdefault("STREAMLIT_SERVER_HEADLESS", "true")
        os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
        
        # Start Streamlit
        subprocess.run([
            "streamlit", "run", "app.py",
            "--server.port", os.environ["STREAMLIT_SERVER_PORT"],
            "--server.address", os.environ["STREAMLIT_SERVER_ADDRESS"],
            "--server.headless", "true"
        ])
        
    except Exception as e:
        logger.error(f"❌ Error starting Streamlit: {e}")
        sys.exit(1)

def main():
    """Main startup function."""
    logger.info("🚀 Railway Startup Script")
    logger.info("=" * 50)
    
    # Step 1: Create tables
    if not run_table_creation():
        logger.warning("⚠️ Table creation failed, but continuing with app startup")
    
    # Step 2: Start Streamlit
    start_streamlit()

if __name__ == "__main__":
    main()
