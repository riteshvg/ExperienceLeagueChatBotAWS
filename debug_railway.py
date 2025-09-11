#!/usr/bin/env python3
"""
Debug script to test Railway deployment locally.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def test_imports():
    """Test all critical imports."""
    print("🔍 Testing critical imports...")
    
    try:
        import streamlit as st
        print("✅ Streamlit imported")
    except Exception as e:
        print(f"❌ Streamlit import failed: {e}")
        return False
    
    try:
        import boto3
        print("✅ Boto3 imported")
    except Exception as e:
        print(f"❌ Boto3 import failed: {e}")
        return False
    
    try:
        import pandas as pd
        print("✅ Pandas imported")
    except Exception as e:
        print(f"❌ Pandas import failed: {e}")
        return False
    
    try:
        import psycopg2
        print("✅ PostgreSQL driver imported")
    except Exception as e:
        print(f"❌ PostgreSQL import failed: {e}")
        return False
    
    try:
        from src.models.database_models import UserQuery
        print("✅ Database models imported")
    except Exception as e:
        print(f"❌ Database models import failed: {e}")
        return False
    
    return True

def test_app_startup():
    """Test app startup without running Streamlit."""
    print("\n🚀 Testing app startup...")
    
    try:
        # Set environment variables for testing
        os.environ['USE_SQLITE'] = 'true'
        os.environ['SQLITE_DATABASE'] = 'test.db'
        
        # Import the main app module
        import app
        print("✅ App module imported successfully")
        
        # Test configuration loading
        from config.settings import Settings
        settings = Settings()
        print("✅ Settings loaded successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ App startup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🧪 Railway Deployment Debug Test")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_app_startup
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 40)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! App should work on Railway.")
    else:
        print("❌ Some tests failed. Check the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
