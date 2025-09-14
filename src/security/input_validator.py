"""
Input Validation and Sanitization for Security
Protects against SQL injection, XSS, command injection, and other attacks
"""

import re
import html
import urllib.parse
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of input validation"""
    is_valid: bool
    sanitized_input: str
    threats_detected: List[str]
    risk_level: str  # 'low', 'medium', 'high', 'critical'
    original_input: str

class InputValidator:
    """Comprehensive input validator and sanitizer"""
    
    def __init__(self):
        self.max_input_length = 20000  # AWS Bedrock limit
        self.setup_patterns()
    
    def setup_patterns(self):
        """Setup regex patterns for threat detection"""
        # SQL Injection patterns
        self.sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\b)",
            r"(\s*(;|--|/\*|\*/|@@|@)\s*)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\b(OR|AND)\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?)",
            r"(\bUNION\s+(ALL\s+)?SELECT\b)",
            r"(\bINSERT\s+INTO\b)",
            r"(\bDROP\s+(TABLE|DATABASE|SCHEMA)\b)",
            r"(\bEXEC\s*\()",
            r"(\bWAITFOR\s+DELAY\b)",
            r"(\bSLEEP\s*\()",
        ]
        
        # XSS patterns (enhanced)
        self.xss_patterns = [
            r"<\s*script[^>]*>.*?</\s*script\s*>",
            r"<\s*script[^>]*>",
            r"</\s*script\s*>",
            r"<\s*img[^>]*on\w+\s*=",
            r"<\s*img[^>]*src\s*=\s*['\"]?x['\"]?[^>]*on\w+",
            r"<\s*svg[^>]*on\w+\s*=",
            r"<\s*iframe[^>]*src\s*=\s*['\"]?javascript:",
            r"<\s*object[^>]*data\s*=\s*['\"]?javascript:",
            r"<\s*embed[^>]*src\s*=\s*['\"]?javascript:",
            r"<\s*link[^>]*href\s*=\s*['\"]?javascript:",
            r"<\s*div[^>]*on\w+\s*=",
            r"javascript\s*:",
            r"vbscript\s*:",
            r"on\w+\s*=\s*['\"][^'\"]*['\"]",
            r"on\w+\s*=\s*\w+",
            r"expression\s*\(",
            r"url\s*\(\s*['\"]?javascript:",
            r"<[^>]*on\w+\s*=",
            r"alert\s*\(",
            r"eval\s*\(",
            r"document\.",
            r"window\.",
        ]
        
        # Command injection patterns
        self.command_patterns = [
            r"[\;\|\&\$\`]",
            r"\b(cat|ls|pwd|whoami|id|uname|ps|kill|rm|cp|mv|chmod|chown)\b",
            r"\b(wget|curl|nc|netcat|telnet|ssh|ftp)\b",
            r"\b(python|python3|perl|ruby|bash|sh|zsh|cmd|powershell)\b",
            r"(\|\s*(cat|more|less|head|tail|grep|awk|sed))",
            r"(\&\&|\|\|)",
            r"(\$\(|\`)",
        ]
        
        # Path traversal patterns (enhanced)
        self.path_patterns = [
            r"\.\.[\\/]",
            r"\.\.[\\/]\.\.[\\/]",
            r"%2e%2e[\\/]",
            r"%252e%252e[\\/]",
            r"\.\.%2f",
            r"\.\.%5c",
            r"..%252f",
            r"..%255c",
            r"\.\./",
            r"\.\.\\",
            r"\.\./\.\./",
            r"\.\.\\\.\.\\",
            r"(?i)\.\.[\\/]",
            r"(?i)etc[\\/]passwd",
            r"(?i)windows[\\/]system32",
            r"(?i)etc[\\/]shadow",
            r"(?i)boot\.ini",
            r"(?i)web\.config",
            r"/var/",
            r"/etc/",
            r"/root/",
            r"c:\\\\",
            r"d:\\\\",
        ]
        
        # Compile patterns for better performance
        self.compiled_sql = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in self.sql_patterns]
        self.compiled_xss = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in self.xss_patterns]
        self.compiled_command = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in self.command_patterns]
        self.compiled_path = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in self.path_patterns]
    
    def validate_input(self, user_input: str, input_type: str = "general") -> ValidationResult:
        """
        Comprehensive input validation and sanitization
        
        Args:
            user_input: The input to validate
            input_type: Type of input ('query', 'admin', 'file', 'general')
            
        Returns:
            ValidationResult with validation status and sanitized input
        """
        threats_detected = []
        risk_level = "low"
        
        try:
            # Basic validation
            if not user_input or not isinstance(user_input, str):
                return ValidationResult(
                    is_valid=False,
                    sanitized_input="",
                    threats_detected=["empty_or_invalid_input"],
                    risk_level="medium",
                    original_input=str(user_input) if user_input else ""
                )
            
            # Length check with improved buffer overflow detection
            if len(user_input) > self.max_input_length:
                threats_detected.append("excessive_length")
                risk_level = "high"
                
                # Critical buffer overflow attempt (more than 2x limit)
                if len(user_input) > self.max_input_length * 2:
                    return ValidationResult(
                        is_valid=False,
                        sanitized_input="",
                        threats_detected=["buffer_overflow_attempt"],
                        risk_level="critical",
                        original_input=user_input[:100] + "..."  # Log only first 100 chars
                    )
                # Medium overflow (1.25x - 2x limit)
                elif len(user_input) > self.max_input_length * 1.25:
                    threats_detected.append("potential_buffer_overflow")
                    risk_level = "high"
            
            # Check for suspicious patterns
            sql_threats = self._detect_sql_injection(user_input)
            xss_threats = self._detect_xss(user_input)
            command_threats = self._detect_command_injection(user_input)
            path_threats = self._detect_path_traversal(user_input)
            
            threats_detected.extend(sql_threats)
            threats_detected.extend(xss_threats)
            threats_detected.extend(command_threats)
            threats_detected.extend(path_threats)
            
            # Determine risk level
            if sql_threats or command_threats:
                risk_level = "critical"
            elif xss_threats or path_threats:
                risk_level = "high"
            elif len(threats_detected) > 0:
                risk_level = "medium"
            
            # Sanitize input
            sanitized_input = self._sanitize_input(user_input, input_type)
            
            # Final validation
            is_valid = self._is_safe_input(sanitized_input, threats_detected, risk_level)
            
            return ValidationResult(
                is_valid=is_valid,
                sanitized_input=sanitized_input,
                threats_detected=threats_detected,
                risk_level=risk_level,
                original_input=user_input[:500] + "..." if len(user_input) > 500 else user_input
            )
            
        except Exception as e:
            logger.error(f"Error during input validation: {e}")
            return ValidationResult(
                is_valid=False,
                sanitized_input="",
                threats_detected=["validation_error"],
                risk_level="critical",
                original_input=str(user_input)[:100] + "..."
            )
    
    def _detect_sql_injection(self, text: str) -> List[str]:
        """Detect SQL injection patterns"""
        threats = []
        for pattern in self.compiled_sql:
            if pattern.search(text):
                threats.append("sql_injection")
                break
        return threats
    
    def _detect_xss(self, text: str) -> List[str]:
        """Detect XSS patterns"""
        threats = []
        for pattern in self.compiled_xss:
            if pattern.search(text):
                threats.append("xss_attempt")
                break
        return threats
    
    def _detect_command_injection(self, text: str) -> List[str]:
        """Detect command injection patterns"""
        threats = []
        for pattern in self.compiled_command:
            if pattern.search(text):
                threats.append("command_injection")
                break
        return threats
    
    def _detect_path_traversal(self, text: str) -> List[str]:
        """Detect path traversal patterns"""
        threats = []
        for pattern in self.compiled_path:
            if pattern.search(text):
                threats.append("path_traversal")
                break
        return threats
    
    def _sanitize_input(self, text: str, input_type: str) -> str:
        """Sanitize input based on type"""
        try:
            # Basic HTML escaping
            sanitized = html.escape(text)
            
            # URL decode to prevent encoded attacks
            sanitized = urllib.parse.unquote(sanitized)
            
            # Remove null bytes
            sanitized = sanitized.replace('\x00', '')
            
            # Normalize whitespace
            sanitized = ' '.join(sanitized.split())
            
            # Input-type specific sanitization
            if input_type == "query":
                # For chat queries, be more permissive but safe
                sanitized = self._sanitize_query(sanitized)
            elif input_type == "admin":
                # For admin inputs, be more restrictive
                sanitized = self._sanitize_admin_input(sanitized)
            elif input_type == "file":
                # For file paths, be very restrictive
                sanitized = self._sanitize_file_path(sanitized)
            
            return sanitized
            
        except Exception as e:
            logger.error(f"Error during input sanitization: {e}")
            return ""
    
    def _sanitize_query(self, text: str) -> str:
        """Sanitize chat query input"""
        # Remove potentially dangerous characters but keep question marks, etc.
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '|', '`', '$']
        for char in dangerous_chars:
            text = text.replace(char, '')
        return text
    
    def _sanitize_admin_input(self, text: str) -> str:
        """Sanitize admin panel input"""
        # Very restrictive sanitization for admin inputs
        allowed_chars = re.compile(r'[^a-zA-Z0-9\s\-_@.]+')
        return allowed_chars.sub('', text)
    
    def _sanitize_file_path(self, text: str) -> str:
        """Sanitize file path input"""
        # Only allow safe characters for file paths
        allowed_chars = re.compile(r'[^a-zA-Z0-9\-_./]+')
        sanitized = allowed_chars.sub('', text)
        
        # Remove path traversal attempts
        sanitized = sanitized.replace('..', '')
        sanitized = sanitized.replace('//', '/')
        
        return sanitized
    
    def _is_safe_input(self, sanitized_input: str, threats: List[str], risk_level: str) -> bool:
        """Determine if input is safe after sanitization"""
        # Critical threats are never allowed
        if risk_level == "critical":
            return False
        
        # High risk requires manual review (for now, block)
        if risk_level == "high" and len(threats) > 2:
            return False
        
        # Check if sanitized input is significantly different (potential attack)
        if len(sanitized_input) < len(threats) * 10:  # Arbitrary threshold
            return False
        
        return True


class SecurityValidator:
    """High-level security validator for the application"""
    
    def __init__(self):
        self.input_validator = InputValidator()
        self.blocked_ips = set()
        self.failed_attempts = {}
    
    def validate_chat_query(self, query: str) -> Tuple[bool, str, List[str]]:
        """
        Validate chat query input
        
        Returns:
            (is_valid, sanitized_query, threats_detected)
        """
        result = self.input_validator.validate_input(query, "query")
        
        if not result.is_valid:
            logger.warning(f"Blocked malicious query: {result.threats_detected}")
        
        return result.is_valid, result.sanitized_input, result.threats_detected
    
    def validate_admin_input(self, admin_input: str) -> Tuple[bool, str, List[str]]:
        """
        Validate admin panel input
        
        Returns:
            (is_valid, sanitized_input, threats_detected)
        """
        result = self.input_validator.validate_input(admin_input, "admin")
        
        if not result.is_valid:
            logger.warning(f"Blocked malicious admin input: {result.threats_detected}")
        
        return result.is_valid, result.sanitized_input, result.threats_detected
    
    def validate_file_path(self, file_path: str) -> Tuple[bool, str, List[str]]:
        """
        Validate file path input
        
        Returns:
            (is_valid, sanitized_path, threats_detected)
        """
        result = self.input_validator.validate_input(file_path, "file")
        
        if not result.is_valid:
            logger.warning(f"Blocked malicious file path: {result.threats_detected}")
        
        return result.is_valid, result.sanitized_input, result.threats_detected


# Create global instance
security_validator = SecurityValidator()
