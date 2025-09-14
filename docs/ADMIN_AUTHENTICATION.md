# Admin Panel Authentication Guide

This document explains the different authentication options available for securing the admin panel.

## 🔐 Current Implementation

### Basic Password Authentication (Active)

- **Password**: Stored in `.streamlit/secrets.toml`
- **Default Password**: `admin123`
- **Session**: Persistent until logout or timeout
- **Security**: Basic password protection

## 🛡️ Available Authentication Methods

### 1. Simple Password Protection ✅ (Implemented)

```toml
# .streamlit/secrets.toml
ADMIN_PASSWORD = "your_secure_password"
```

**Pros:**

- Easy to implement
- No external dependencies
- Quick setup

**Cons:**

- Single password for all users
- Password stored in configuration

### 2. Advanced Password Protection (Available)

```python
# Uses src/auth/admin_auth.py
from src.auth.admin_auth import check_admin_access_with_options
```

**Features:**

- Multiple failed attempt lockout
- Session timeout
- Attempt tracking
- Configurable security settings

**Configuration:**

```toml
ADMIN_PASSWORD = "your_secure_password"
ADMIN_SESSION_TIMEOUT = 3600  # 1 hour
ADMIN_MAX_ATTEMPTS = 3
ADMIN_LOCKOUT_DURATION = 900  # 15 minutes
```

### 3. IP Address Whitelist (Available)

```toml
# .streamlit/secrets.toml
ADMIN_WHITELIST_IPS = "192.168.1.100,10.0.0.50,203.0.113.1"
```

**Pros:**

- Very secure
- No passwords needed
- Works with VPNs

**Cons:**

- Requires static IP
- Less flexible for remote access

### 4. Multiple Admin Users (Available)

```toml
# .streamlit/secrets.toml
ADMIN_PASSWORDS = "admin123,secure456,admin789"
```

**Pros:**

- Multiple admin accounts
- Individual access control
- Easy to manage

### 5. Time-based Access (Available)

```toml
# .streamlit/secrets.toml
ADMIN_ACCESS_START = "09:00"
ADMIN_ACCESS_END = "17:00"
```

**Pros:**

- Restricts access to business hours
- Additional security layer

## 🚀 How to Switch Authentication Methods

### Option A: Keep Current Simple Authentication

No changes needed. Current implementation is active.

### Option B: Switch to Advanced Authentication

1. Update `app.py`:

```python
# Replace this line:
if not check_admin_access():

# With this:
from src.auth.admin_auth import check_admin_access_with_options
if not check_admin_access_with_options():
```

### Option C: Add IP Whitelist

1. Add your IP to `.streamlit/secrets.toml`:

```toml
ADMIN_WHITELIST_IPS = "your.ip.address.here"
```

2. Update `app.py` to use advanced authentication (Option B)

### Option D: Multiple Admin Users

1. Add passwords to `.streamlit/secrets.toml`:

```toml
ADMIN_PASSWORDS = "admin123,secure456,admin789"
```

2. Update the authentication logic in `src/auth/admin_auth.py`

## 🔧 Configuration Options

### Basic Security Settings

```toml
# .streamlit/secrets.toml
ADMIN_PASSWORD = "your_secure_password"
ADMIN_SESSION_TIMEOUT = 3600  # Session timeout in seconds
ADMIN_MAX_ATTEMPTS = 3         # Max failed attempts
ADMIN_LOCKOUT_DURATION = 900   # Lockout duration in seconds
```

### Advanced Security Settings

```toml
# .streamlit/secrets.toml
# IP Whitelist (comma-separated)
ADMIN_WHITELIST_IPS = "192.168.1.100,10.0.0.50"

# Multiple Admin Passwords (comma-separated)
ADMIN_PASSWORDS = "admin123,secure456,admin789"

# Time-based Access (24-hour format)
ADMIN_ACCESS_START = "09:00"
ADMIN_ACCESS_END = "17:00"
```

## 🛡️ Security Best Practices

### 1. Change Default Password

```toml
ADMIN_PASSWORD = "your_very_secure_password_here"
```

### 2. Use Strong Passwords

- At least 12 characters
- Mix of letters, numbers, symbols
- Avoid common words

### 3. Regular Password Updates

- Change password monthly
- Use unique passwords
- Don't reuse passwords

### 4. Monitor Access

- Check logs regularly
- Monitor failed attempts
- Review session times

### 5. Backup Access

- Keep backup admin credentials
- Store securely offline
- Test access regularly

## 🚨 Troubleshooting

### "Account Locked" Error

- Wait 15 minutes for lockout to expire
- Or restart the application to reset attempts

### "Invalid Password" Error

- Check password in `.streamlit/secrets.toml`
- Ensure no extra spaces
- Case-sensitive

### "Access Denied" Error

- Check IP whitelist if enabled
- Verify your IP address
- Contact system administrator

### Session Timeout

- Login again
- Increase `ADMIN_SESSION_TIMEOUT` if needed

## 📝 File Locations

- **Main Authentication**: `app.py` (lines 981-1013)
- **Advanced Authentication**: `src/auth/admin_auth.py`
- **Configuration**: `.streamlit/secrets.toml`
- **Admin Panel**: `src/admin/admin_panel.py`

## 🔄 Switching Between Methods

To switch authentication methods, simply update the import and function call in `app.py`:

```python
# Current (Simple)
if not check_admin_access():

# Advanced
from src.auth.admin_auth import check_admin_access_with_options
if not check_admin_access_with_options():
```

## 📞 Support

If you need help with authentication setup or have security concerns, please contact the system administrator.
