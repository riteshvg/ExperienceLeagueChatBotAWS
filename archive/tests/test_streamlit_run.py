#!/usr/bin/env python3
"""
Test script to run Streamlit app and capture errors
"""

import subprocess
import sys
import os
import time
import signal
import threading

def run_streamlit_test():
    """Run Streamlit app and capture output"""
    print("🚀 Testing Streamlit App Execution")
    print("=" * 50)
    
    # Change to project directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Command to run Streamlit
    cmd = [
        sys.executable, "-m", "streamlit", "run", 
        "src/performance/working_optimized_app.py",
        "--server.headless", "true",
        "--server.port", "8503",
        "--server.address", "localhost"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    print("\nStarting Streamlit app...")
    
    try:
        # Start the process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Read output for 30 seconds
        start_time = time.time()
        output_lines = []
        
        while time.time() - start_time < 30:
            if process.poll() is not None:
                # Process has ended
                break
                
            try:
                line = process.stdout.readline()
                if line:
                    output_lines.append(line.strip())
                    print(f"OUTPUT: {line.strip()}")
                    
                    # Check for success indicators
                    if "You can now view your Streamlit app" in line:
                        print("✅ Streamlit app started successfully!")
                        return True
                    elif "Error" in line or "Exception" in line:
                        print(f"❌ Error detected: {line.strip()}")
                        return False
                        
            except Exception as e:
                print(f"Error reading output: {e}")
                break
        
        # If we get here, the process is still running
        print("⏰ Process still running after 30 seconds")
        
        # Terminate the process
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        
        return False
        
    except Exception as e:
        print(f"❌ Failed to run Streamlit: {e}")
        return False

def test_imports():
    """Test that all imports work"""
    print("\n🧪 Testing Imports...")
    
    try:
        # Test basic imports
        import streamlit as st
        print("✅ Streamlit imported")
        
        # Test our app imports
        sys.path.insert(0, '.')
        from src.performance.working_optimized_app import OptimizedStreamlitApp
        print("✅ OptimizedStreamlitApp imported")
        
        # Test app creation
        app = OptimizedStreamlitApp()
        print("✅ App created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🔍 Comprehensive Streamlit App Test")
    print("=" * 60)
    
    # Test imports first
    if not test_imports():
        print("\n❌ Import tests failed. Cannot proceed with Streamlit test.")
        return False
    
    # Test Streamlit execution
    if run_streamlit_test():
        print("\n🎉 Streamlit app test passed!")
        return True
    else:
        print("\n❌ Streamlit app test failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
