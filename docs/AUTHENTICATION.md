# Authentication Flow

How authentication works in Chatter.

## Overview

Chatter uses JWT (JSON Web Token) based authentication with secure HTTP-only cookies. This provides:
- ✅ Secure token storage (httponly prevents XSS)
- ✅ Cross-domain authentication (kevsrobots.com ↔ chatter.kevsrobots.com)
- ✅ Stateless authentication (no server-side sessions)
- ✅ Username display for UI (separate non-httponly cookie)

## Authentication Methods

### 1. Form-Based Authentication (Primary)

Used by web UI at chatter.kevsrobots.com.

**Flow:**
```
User → Login Form → POST /login
  ↓
Validate Credentials
  ↓
Generate JWT Token
  ↓
Set Cookies:
  - access_token (httponly)
  - username (readable by JS)
  ↓
Redirect to /account or return_to URL
```

### 2. API Authentication (Deprecated)

OAuth2 password flow for backward compatibility.

**Flow:**
```
Client → POST /api/login (form data)
  ↓
Validate Credentials
  ↓
Generate JWT Token
  ↓
Return JSON: {"access_token": "...", "token_type": "bearer"}
```

---

## JWT Token Structure

### Token Claims

```json
{
  "sub": "johndoe",           // Subject: username
  "exp": 1698076800,          // Expiration: 30 minutes from creation
  "iat": 1698075000           // Issued at: current timestamp
}
```

### Token Configuration

- **Algorithm:** HS256 (HMAC with SHA-256)
- **Secret Key:** Configured via `SECRET_KEY` environment variable
- **Expiration:** 30 minutes from creation
- **Issuer:** Not specified
- **Audience:** Not specified

---

## Cookie Configuration

### Production (HTTPS)

Two cookies are set after successful login:

**access_token Cookie:**
```
Name: access_token
Value: Bearer eyJhbGciOiJIUzI1NiIs...
Domain: .kevsrobots.com
Path: /
HttpOnly: true
Secure: true (HTTPS only)
SameSite: Lax
Max-Age: 1800 seconds (30 minutes)
```

**username Cookie:**
```
Name: username
Value: johndoe
Domain: .kevsrobots.com
Path: /
HttpOnly: false (JavaScript can read)
Secure: true (HTTPS only)
SameSite: Lax
Max-Age: 1800 seconds (30 minutes)
```

### Development (HTTP)

Same cookies but `Secure` flag is disabled and `Domain` is not set:

```
HttpOnly: true/false
Secure: false
SameSite: Lax
Domain: (not set - defaults to current domain)
```

---

## Cross-Domain Authentication

Chatter enables authentication across subdomains:

**Cookie Domain:** `.kevsrobots.com`
- Cookies are sent to `chatter.kevsrobots.com`
- Cookies are sent to `www.kevsrobots.com`
- Cookies are sent to any `*.kevsrobots.com` subdomain

**CORS Configuration:**
```python
ALLOWED_ORIGINS = [
    "https://www.kevsrobots.com",
    "https://kevsrobots.com",
    "http://localhost:4000",
    "http://local.kevsrobots.com:4000"
]
```

**Why Two Cookies?**
- `access_token` - Secure JWT for server-side validation (httponly prevents JavaScript access)
- `username` - UI display only (JavaScript can read to show username in navigation)

---

## Authentication Flows

### Registration Flow

```
1. User visits /register
   ↓
2. User fills form:
   - username
   - firstname
   - lastname
   - email
   - password
   - date_of_birth (optional)
   ↓
3. POST /register
   ↓
4. Validate input:
   - Username unique?
   - Email unique?
   - Password >= 8 chars?
   ↓
5. Hash password (bcrypt)
   ↓
6. Create user record
   ↓
7. Log 'created' action to accountlog
   ↓
8. Redirect to /login
```

### Login Flow

```
1. User visits /login
   ↓
2. User enters:
   - username
   - password
   ↓
3. POST /login
   ↓
4. Find user by username
   ↓
5. Verify password (bcrypt)
   ↓
6. Check if force_password_reset = true
   ├─ YES → Redirect to /force-password-reset
   └─ NO  → Continue
   ↓
7. Generate JWT token
   ↓
8. Set cookies (access_token, username)
   ↓
9. Update last_login timestamp
   ↓
10. Redirect to /account or return_to URL
```

### Protected Route Access

```
1. User requests /account
   ↓
2. Middleware checks for access_token cookie
   ↓
3. Extract JWT from cookie
   ↓
4. Verify JWT signature
   ↓
5. Check if token expired
   ├─ EXPIRED → 401 Unauthorized
   └─ VALID   → Continue
   ↓
6. Extract username from token claims
   ↓
7. Load user from database
   ├─ NOT FOUND → 401 Unauthorized
   └─ FOUND     → Continue
   ↓
8. Attach user to request context
   ↓
9. Execute route handler
```

### Logout Flow

```
1. User clicks logout
   ↓
2. GET /logout
   ↓
3. Clear cookies:
   - Delete access_token
   - Delete username
   ↓
4. Redirect to /login
```

---

## Security Features

### Password Hashing

**Algorithm:** bcrypt with cost factor 12

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hash password
hashed = pwd_context.hash("my_password")
# Result: $2b$12$KIX3vZ9Yt8... (60 chars)

# Verify password
is_valid = pwd_context.verify("my_password", hashed)
# Returns: True/False
```

**Why bcrypt?**
- Adaptive hashing (cost factor can be increased over time)
- Built-in salt (prevents rainbow table attacks)
- Deliberately slow (prevents brute force attacks)

### Rate Limiting

Prevents brute force attacks:

| Endpoint | Limit | Window |
|----------|-------|--------|
| POST /login | 5 requests | 1 minute |
| POST /api/login | 5 requests | 1 minute |
| POST /register | 3 requests | 1 hour |

**Implementation:** Using `slowapi` middleware

**Response when exceeded:**
```
HTTP 429 Too Many Requests
{
  "detail": "Rate limit exceeded"
}
```

### Session Security

✅ **HttpOnly Cookies** - Prevents XSS attacks from stealing tokens
✅ **Secure Flag** - HTTPS-only in production
✅ **SameSite=Lax** - Prevents CSRF attacks
✅ **Token Expiration** - 30-minute lifetime
✅ **No Server-Side Sessions** - Stateless (scales horizontally)

### Account Security

✅ **Password Requirements** - Minimum 8 characters
✅ **Unique Constraints** - Username and email must be unique
✅ **Account Status** - Can disable accounts (status='inactive')
✅ **Audit Logging** - All account changes logged to accountlog
✅ **Force Password Reset** - Admins can require password change
✅ **One-Time Reset Codes** - Expire after 24 hours, single use

---

## Admin Authentication

Admins are identified by `user.type = 1`.

**Admin Dependency:**
```python
def get_current_admin(current_user: User = Depends(get_current_user)):
    """Check if current user is an admin"""
    if current_user.type != 1:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
```

**Protected Admin Routes:**
- GET /admin
- POST /admin/generate-reset-code/{user_id}
- POST /admin/force-password-reset/{user_id}

---

## Token Refresh

**Current Behavior:** No automatic token refresh

**Expiration Handling:**
- Token expires after 30 minutes
- User must login again
- No refresh token mechanism

**Future Enhancement:** Consider adding refresh tokens for longer sessions

---

## Troubleshooting

### Common Authentication Issues

**Issue:** "Invalid credentials" error

**Causes:**
- Wrong username or password
- Account inactive (status != 'active')
- Password not hashed correctly

**Solution:**
```sql
-- Check user exists
SELECT username, status FROM "user" WHERE username = 'johndoe';

-- Verify password hash
-- (Use Python to verify: pwd_context.verify(password, hash))
```

---

**Issue:** Cookies not persisting

**Causes:**
- Browser blocking third-party cookies
- Domain mismatch (localhost vs local.kevsrobots.com)
- HTTP vs HTTPS mismatch

**Solution:**
- In development: Use `local.kevsrobots.com` in /etc/hosts
- Check browser cookie settings
- Verify ENVIRONMENT variable is set correctly

---

**Issue:** CORS errors

**Causes:**
- Origin not in ALLOWED_ORIGINS
- Credentials flag not set

**Solution:**
```python
# Update ALLOWED_ORIGINS in .env
ALLOWED_ORIGINS=https://www.kevsrobots.com,https://kevsrobots.com

# Ensure credentials enabled in fetch
fetch('https://chatter.kevsrobots.com/api/endpoint', {
  credentials: 'include'
})
```

---

**Issue:** Token expired

**Causes:**
- User session idle for > 30 minutes
- System clock skew

**Solution:**
- User must login again
- Verify server time is accurate
- Consider implementing refresh tokens

---

## Security Best Practices

1. **Never log passwords** - Even in debug mode
2. **Rotate SECRET_KEY regularly** - Update in production .env
3. **Use HTTPS in production** - Always set `Secure` flag on cookies
4. **Monitor failed login attempts** - Watch for brute force attacks
5. **Implement account lockout** - After N failed attempts (future enhancement)
6. **Review audit logs regularly** - Check accountlog for suspicious activity
7. **Keep dependencies updated** - Especially security-related packages

---

## Environment Variables

Authentication-related configuration:

```bash
# Required
SECRET_KEY=your-secret-key-here  # Generate with: openssl rand -hex 32
DATABASE_URL=postgresql://user:pass@host:port/dbname

# Optional
ENVIRONMENT=production  # or 'development'
ALLOWED_ORIGINS=https://www.kevsrobots.com,https://kevsrobots.com
```

**Never commit secrets to git!**
- Use `.env` file (in `.gitignore`)
- Use environment variables in production
- Provide `.env.example` template

---

## Testing Authentication

### Manual Testing

```bash
# Register user
curl -X POST https://chatter.kevsrobots.com/register \
  -F "username=testuser" \
  -F "firstname=Test" \
  -F "lastname=User" \
  -F "email=test@example.com" \
  -F "password=TestPass123"

# Login
curl -X POST https://chatter.kevsrobots.com/login \
  -F "username=testuser" \
  -F "password=TestPass123" \
  -c cookies.txt

# Access protected route
curl https://chatter.kevsrobots.com/account \
  -b cookies.txt
```

### Automated Testing

See [TESTING.md](TESTING.md) for unit and integration tests.
