# Production Security Testing Guide

## Overview

This guide provides comprehensive instructions for testing the security measures implemented in your Adobe Analytics RAG application in a production environment.

## Security Measures Implemented

### 1. Input Validation & Sanitization

- **Location**: `src/security/input_validator.py`
- **Features**: SQL injection, XSS, command injection, path traversal protection
- **Integration**: Applied to all user inputs in `app.py`

### 2. Admin Authentication

- **Location**: `src/auth/admin_auth.py`
- **Features**: Role-based access control, secure session management
- **Integration**: Applied to admin panel routes

## Testing Methods

### Method 1: Direct Application Testing

#### Start the Application

```bash
# Navigate to your project directory
cd /Users/ritesh/adobe-analytics-rag

# Start the Streamlit application
streamlit run app.py
```

#### Test Security Measures

1. **SQL Injection Testing**

   - Open the application in your browser
   - Try entering malicious SQL queries in any input field
   - Examples to test:
     ```
     '; DROP TABLE users; --
     ' OR '1'='1
     ' UNION SELECT * FROM users --
     ```

2. **XSS Testing**

   - Test with script injection attempts:
     ```
     <script>alert('XSS')</script>
     <img src=x onerror=alert('XSS')>
     javascript:alert('XSS')
     ```

3. **Command Injection Testing**

   - Test with system command attempts:
     ```
     ; ls -la
     | cat /etc/passwd
     && rm -rf /
     ```

4. **Path Traversal Testing**
   - Test with directory traversal attempts:
     ```
     ../../../etc/passwd
     ..\..\..\windows\system32\drivers\etc\hosts
     %2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd
     ```

### Method 2: Automated Testing Script

#### Run the Security Test Suite

```bash
# Run the comprehensive security tests
python test_security.py
```

This will test:

- All input validation rules
- SQL injection prevention
- XSS protection
- Command injection protection
- Path traversal protection
- Admin authentication

### Method 3: Manual Browser Testing

#### Test Admin Authentication

1. Navigate to admin routes without authentication
2. Try to access admin panel directly
3. Test with invalid credentials
4. Test session management

#### Test Input Fields

1. Try various malicious inputs in all form fields
2. Test file upload functionality
3. Test URL parameters
4. Test JSON payloads

### Method 4: Production Environment Testing

#### Deploy to Production

```bash
# If using Railway
railway up

# If using other platforms, follow their deployment process
```

#### Test in Production

1. Access your production URL
2. Run the same security tests as in development
3. Monitor logs for security events
4. Test with real user scenarios

## Expected Security Behavior

### ✅ What Should Happen (Security Working)

- Malicious inputs should be blocked or sanitized
- SQL injection attempts should be prevented
- XSS scripts should not execute
- Command injection should be blocked
- Path traversal should be prevented
- Admin routes should require authentication
- Invalid inputs should show appropriate error messages

### ❌ What Should NOT Happen (Security Failing)

- Database errors or crashes
- Script execution in browser
- System command execution
- File system access outside allowed directories
- Unauthorized access to admin functions
- Sensitive data exposure in error messages

## Monitoring and Logging

### Check Security Logs

```bash
# Check application logs for security events
tail -f logs/security.log

# Check for blocked requests
grep "SECURITY_BLOCKED" logs/application.log
```

### Monitor Performance

- Security measures should not significantly impact performance
- Response times should remain acceptable
- Memory usage should be stable

## Troubleshooting

### Common Issues

1. **False Positives**: Legitimate inputs being blocked
2. **Performance Impact**: Security checks slowing down the app
3. **Integration Issues**: Security layer not properly integrated

### Solutions

1. Adjust validation rules in `input_validator.py`
2. Optimize security checks for better performance
3. Ensure proper integration in `app.py`

## Security Testing Checklist

- [ ] SQL injection protection working
- [ ] XSS protection working
- [ ] Command injection protection working
- [ ] Path traversal protection working
- [ ] Admin authentication working
- [ ] Input validation working
- [ ] Error handling secure
- [ ] Logging working
- [ ] Performance acceptable
- [ ] No false positives

## Next Steps

1. Run the security tests
2. Fix any issues found
3. Deploy to production
4. Monitor security events
5. Regular security audits

## Support

If you encounter issues:

1. Check the logs for error messages
2. Review the security configuration
3. Test individual components
4. Contact the development team

---

**Note**: Always test in a safe environment first. Never test security measures on production systems with real data without proper backups.
