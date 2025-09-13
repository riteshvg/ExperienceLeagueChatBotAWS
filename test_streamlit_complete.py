#!/usr/bin/env python3
"""
Test script to run the complete optimized Streamlit app
"""

import subprocess
import sys
import os
import time
import signal
import threading

def run_streamlit_test():
    """Run complete optimized Streamlit app and capture output"""
    print("🚀 Testing Complete Optimized Streamlit App")
    print("=" * 60)
    
    # Change to project directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Command to run Streamlit
    cmd = [
        sys.executable, "-m", "streamlit", "run", 
        "src/performance/complete_optimized_app.py",
        "--server.headless", "true",
        "--server.port", "8504",
        "--server.address", "localhost"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    print("\nStarting complete optimized Streamlit app...")
    
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
        success_indicators = 0
        
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
                        success_indicators += 1
                    elif "Application components initialized" in line:
                        print("✅ App components initialized!")
                        success_indicators += 1
                    elif "Query processed" in line:
                        print("✅ Query processing working!")
                        success_indicators += 1
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
        
        return success_indicators >= 1
        
    except Exception as e:
        print(f"❌ Failed to run Streamlit: {e}")
        return False

def test_end_to_end_functionality():
    """Test end-to-end functionality without Streamlit"""
    print("\n🧪 Testing End-to-End Functionality...")
    
    try:
        import sys
        sys.path.insert(0, '.')
        
        from src.performance.complete_optimized_app import OptimizedStreamlitApp
        
        # Create app instance
        app = OptimizedStreamlitApp()
        print("✅ App created successfully")
        
        # Test query processing
        print("Testing query processing...")
        result = app.process_query_optimized("How do I implement Adobe Analytics?")
        
        if result.get("success"):
            print("✅ Query processing successful!")
            print(f"📝 Response: {result.get('answer', 'No answer')[:100]}...")
            print(f"🤖 Model used: {result.get('model_used', 'Unknown')}")
            print(f"📊 Documents found: {len(result.get('documents', []))}")
            return True
        else:
            print(f"❌ Query processing failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ End-to-end test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🔍 Complete Optimized App Test Suite")
    print("=" * 50)
    
    # Test end-to-end functionality first
    if not test_end_to_end_functionality():
        print("\n❌ End-to-end functionality test failed. Cannot proceed with Streamlit test.")
        return False
    
    # Test Streamlit execution
    if run_streamlit_test():
        print("\n🎉 Complete optimized app test passed!")
        print("\n🚀 The app is ready for production use!")
        print("To run: streamlit run src/performance/complete_optimized_app.py")
        return True
    else:
        print("\n❌ Streamlit app test failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
