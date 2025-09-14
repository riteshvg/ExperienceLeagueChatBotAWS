#!/usr/bin/env python3
"""
Script to start the application and run security tests
"""

import subprocess
import time
import sys
import os
import signal
import requests
from test_production_security import ProductionSecurityTester

def check_application_running(url: str, max_attempts: int = 30) -> bool:
    """Check if the application is running and accessible"""
    for attempt in range(max_attempts):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        
        print(f"⏳ Waiting for application to start... (attempt {attempt + 1}/{max_attempts})")
        time.sleep(2)
    
    return False

def start_application():
    """Start the Streamlit application"""
    print("🚀 Starting Adobe Analytics RAG Application...")
    
    # Start the application in the background
    process = subprocess.Popen(
        ["streamlit", "run", "app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid if os.name != 'nt' else None
    )
    
    return process

def run_security_tests():
    """Run the security tests"""
    print("\n🔒 Running Security Tests...")
    
    tester = ProductionSecurityTester()
    results = tester.run_all_tests()
    tester.print_results(results)
    
    return results

def main():
    """Main function"""
    print("=" * 60)
    print("🔐 ADOBE ANALYTICS RAG - SECURITY TESTING")
    print("=" * 60)
    
    # Start the application
    app_process = start_application()
    
    try:
        # Wait for application to start
        if not check_application_running("http://localhost:8501"):
            print("❌ Failed to start application or application not accessible")
            return 1
        
        print("✅ Application started successfully!")
        
        # Run security tests
        results = run_security_tests()
        
        # Calculate overall success rate
        total_tests = sum(len(test_results) for test_results in results.values())
        total_blocked = sum(
            sum(1 for result in test_results if result.get("blocked", False))
            for test_results in results.values()
        )
        
        success_rate = total_blocked / total_tests * 100 if total_tests > 0 else 0
        
        print(f"\n🎯 Overall Security Score: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print("🎉 Excellent! Security measures are working well.")
        elif success_rate >= 70:
            print("⚠️  Good, but some security improvements needed.")
        else:
            print("🚨 Security measures need immediate attention!")
        
        print(f"\n📱 Application is running at: http://localhost:8501")
        print("Press Ctrl+C to stop the application and exit.")
        
        # Keep the application running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping application...")
            
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return 1
    
    finally:
        # Clean up the process
        try:
            if os.name != 'nt':
                os.killpg(os.getpgid(app_process.pid), signal.SIGTERM)
            else:
                app_process.terminate()
            app_process.wait(timeout=5)
        except:
            try:
                app_process.kill()
            except:
                pass
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
