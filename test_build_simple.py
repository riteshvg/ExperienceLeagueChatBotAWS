#!/usr/bin/env python3
"""
Simple build test without Docker.
"""

import subprocess
import sys
import os

def test_minimal_install():
    """Test minimal requirements installation."""
    print("🧪 Testing Minimal Requirements Installation")
    print("=" * 50)
    
    try:
        # Install minimal requirements
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "--no-cache-dir", "-r", "requirements-minimal.txt"
        ], capture_output=True, text=True, check=True)
        
        print("✅ Minimal requirements installed successfully")
        
        # Test critical imports
        test_imports = [
            "import streamlit as st",
            "import boto3",
            "import pandas as pd", 
            "import psycopg2",
            "from pydantic import BaseModel"
        ]
        
        for import_stmt in test_imports:
            try:
                exec(import_stmt)
                print(f"✅ {import_stmt}")
            except Exception as e:
                print(f"❌ {import_stmt} - {e}")
                return False
        
        print("\n🎉 All tests passed!")
        print("✅ This configuration should work on Railway")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed: {e.stderr}")
        return False

def main():
    """Run the test."""
    if test_minimal_install():
        print("\n📋 Next Steps:")
        print("1. Commit these changes to GitHub")
        print("2. Update Railway to use requirements-minimal.txt")
        print("3. Redeploy on Railway")
        print("4. If Railway still times out, try Render.com or Vercel")
        return 0
    else:
        print("\n❌ Tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    exit(main())
