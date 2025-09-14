"""
Advanced Admin Authentication Options
Multiple authentication methods for admin panel access
"""

import streamlit as st
import os
import hashlib
import time
from datetime import datetime, timedelta

class AdminAuth:
    """Admin authentication manager with multiple security options."""
    
    def __init__(self):
        self.max_attempts = int(st.secrets.get("ADMIN_MAX_ATTEMPTS", 3))
        self.session_timeout = int(st.secrets.get("ADMIN_SESSION_TIMEOUT", 3600))  # 1 hour
        self.attempts_key = "admin_login_attempts"
        self.last_attempt_key = "admin_last_attempt"
        self.session_start_key = "admin_session_start"
    
    def is_authenticated(self):
        """Check if user is currently authenticated."""
        if not st.session_state.get('admin_authenticated', False):
            return False
        
        # Check session timeout
        session_start = st.session_state.get(self.session_start_key, 0)
        if time.time() - session_start > self.session_timeout:
            self.logout()
            return False
        
        return True
    
    def is_locked_out(self):
        """Check if user is locked out due to too many failed attempts."""
        attempts = st.session_state.get(self.attempts_key, 0)
        last_attempt = st.session_state.get(self.last_attempt_key, 0)
        
        # Reset attempts after 15 minutes
        if time.time() - last_attempt > 900:  # 15 minutes
            st.session_state[self.attempts_key] = 0
            return False
        
        return attempts >= self.max_attempts
    
    def record_failed_attempt(self):
        """Record a failed login attempt."""
        attempts = st.session_state.get(self.attempts_key, 0) + 1
        st.session_state[self.attempts_key] = attempts
        st.session_state[self.last_attempt_key] = time.time()
    
    def reset_attempts(self):
        """Reset failed login attempts."""
        if self.attempts_key in st.session_state:
            del st.session_state[self.attempts_key]
        if self.last_attempt_key in st.session_state:
            del st.session_state[self.last_attempt_key]
    
    def login(self, password):
        """Attempt to login with password."""
        if self.is_locked_out():
            return False, "Account locked due to too many failed attempts. Please try again later."
        
        # Get admin password from secrets
        admin_password = st.secrets.get("ADMIN_PASSWORD", "admin123")
        
        if password == admin_password:
            # Successful login
            st.session_state.admin_authenticated = True
            st.session_state[self.session_start_key] = time.time()
            self.reset_attempts()
            return True, "Login successful!"
        else:
            # Failed login
            self.record_failed_attempt()
            remaining = self.max_attempts - st.session_state.get(self.attempts_key, 0)
            return False, f"Invalid password. {remaining} attempts remaining."
    
    def logout(self):
        """Logout and clear session."""
        keys_to_clear = [
            'admin_authenticated',
            self.session_start_key,
            self.attempts_key,
            self.last_attempt_key
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]

def check_admin_access_advanced():
    """Advanced admin access check with multiple security features."""
    auth = AdminAuth()
    
    # Check if already authenticated
    if auth.is_authenticated():
        return True
    
    # Check if locked out
    if auth.is_locked_out():
        st.error("🔒 **Account Locked**")
        st.markdown("Too many failed login attempts. Please try again later.")
        return False
    
    # Show authentication form
    st.markdown("### 🔐 Admin Access Required")
    st.markdown("Please enter the admin password to access the dashboard.")
    
    # Show remaining attempts
    attempts = st.session_state.get(auth.attempts_key, 0)
    if attempts > 0:
        remaining = auth.max_attempts - attempts
        st.warning(f"⚠️ {remaining} attempts remaining")
    
    # Create a form for password input
    with st.form("admin_auth_form"):
        password = st.text_input("Admin Password", type="password", placeholder="Enter admin password")
        submit_button = st.form_submit_button("🔓 Access Admin Panel")
        
        if submit_button:
            success, message = auth.login(password)
            if success:
                st.success(f"✅ {message}")
                st.rerun()
            else:
                st.error(f"❌ {message}")
    
    return False

def check_ip_whitelist():
    """Check if user's IP is whitelisted (if IP whitelist is enabled)."""
    # This would require additional setup to get user's real IP
    # For now, this is a placeholder for IP-based authentication
    whitelisted_ips = st.secrets.get("ADMIN_WHITELIST_IPS", "").split(",")
    if not whitelisted_ips or whitelisted_ips == [""]:
        return True  # No IP restriction
    
    # In a real implementation, you'd get the user's IP here
    # For now, we'll skip IP checking
    return True

def check_admin_access_with_options():
    """Check admin access with multiple authentication options."""
    # Check IP whitelist first (if enabled)
    if not check_ip_whitelist():
        st.error("🚫 **Access Denied**")
        st.markdown("Your IP address is not authorized to access the admin panel.")
        return False
    
    # Use advanced authentication
    return check_admin_access_advanced()
