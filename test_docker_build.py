#!/usr/bin/env python3
"""
Test Docker build locally to validate Railway deployment.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - Success")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - Failed")
        print(f"Error: {e.stderr}")
        return False

def test_docker_build():
    """Test Docker build process."""
    print("🐳 Testing Docker Build for Railway")
    print("=" * 50)
    
    # Check if Docker is available
    if not run_command("docker --version", "Check Docker availability"):
        print("❌ Docker not available. Install Docker to test locally.")
        return False
    
    # Build Docker image
    if not run_command("docker build -t adobe-chatbot .", "Build Docker image"):
        return False
    
    # Test Docker run (without actually starting the app)
    if not run_command("docker run --rm adobe-chatbot python -c 'import streamlit, boto3, pandas; print(\"All imports successful\")'", "Test Docker image imports"):
        return False
    
    print("\n🎉 Docker build test successful!")
    print("✅ This configuration should work on Railway")
    return True

def test_minimal_requirements():
    """Test minimal requirements installation."""
    print("\n📦 Testing Minimal Requirements")
    print("=" * 50)
    
    # Create virtual environment
    if not run_command("python -m venv test_env", "Create test virtual environment"):
        return False
    
    # Activate and install
    if os.name == 'nt':  # Windows
        activate_cmd = "test_env\\Scripts\\activate"
        pip_cmd = "test_env\\Scripts\\pip"
    else:  # Unix/Linux/Mac
        activate_cmd = "source test_env/bin/activate"
        pip_cmd = "test_env/bin/pip"
    
    if not run_command(f"{pip_cmd} install -r requirements-minimal.txt", "Install minimal requirements"):
        return False
    
    # Test imports
    if not run_command(f"{activate_cmd} && python -c 'import streamlit, boto3, pandas, psycopg2; print(\"All imports successful\")'", "Test imports in virtual environment"):
        return False
    
    # Cleanup
    if os.name == 'nt':
        run_command("rmdir /s /q test_env", "Cleanup test environment")
    else:
        run_command("rm -rf test_env", "Cleanup test environment")
    
    print("✅ Minimal requirements test successful!")
    return True

def main():
    """Run all tests."""
    print("🧪 Railway Build Validation Tests")
    print("=" * 50)
    
    tests = [
        test_minimal_requirements,
        test_docker_build
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Railway build should work.")
        print("\n📋 Next Steps:")
        print("1. Update Railway to use requirements-minimal.txt")
        print("2. Redeploy on Railway")
        print("3. Check build logs for success")
    else:
        print("❌ Some tests failed. Check the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
