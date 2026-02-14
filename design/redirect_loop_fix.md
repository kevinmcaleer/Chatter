# Redirect Loop Fix - October 28, 2025

## Problem Description

Found a critical redirect loop issue in the nginx logs:

```
GET /?url=https%3A%2F%2Fwww.kevsrobots.com%2Fregister%3Freturn_to%3Dhttps%253A%252F%252Fwww.kevsrobots.com%252Fregister%253Freturn_to%253Dhttps%25253A%25252F%25252Fwww.kevsrobots.com%25252Flogin%25253Freturn_to%25253Dhttps%2525253A%2525252F%2525252Fwww.kevsrobots.com%2525252Flogin...
```

The `return_to` parameter was being URL-encoded recursively, creating an infinite redirect chain between `/login` and `/register` pages. This caused:
- Extremely long URLs (thousands of characters)
- 522 timeout errors
- Server resource exhaustion
- Poor user experience

## Root Cause

The login and register endpoints were:
1. **Not validating `return_to` parameter** - accepting any value including `/login` and `/register`
2. **Not preventing external redirects** - could redirect to `http://evil.com`
3. **Creating infinite loops** - `/login?return_to=/register?return_to=/login...`
4. **No length limits** - URLs could grow indefinitely

## Solution Implemented

### 1. Created `sanitize_return_to()` Function

**File**: `app/auth.py`

```python
def sanitize_return_to(return_to: Optional[str]) -> Optional[str]:
    """
    Sanitize return_to parameter to prevent redirect loops and open redirects.
    Only allow relative URLs (no protocol, no external domains).
    Prevent redirect loops by rejecting return_to that points to /login or /register.
    """
    if not return_to:
        return None

    # Strip whitespace
    return_to = return_to.strip()

    # Reject if empty after stripping
    if not return_to:
        return None

    # Reject absolute URLs (with protocol)
    if return_to.startswith(('http://', 'https://', '//', 'ftp://', 'file://')):
        return None

    # Ensure it starts with /
    if not return_to.startswith('/'):
        return_to = '/' + return_to

    # Reject if return_to points to login or register pages (prevents loops)
    if return_to.startswith('/login') or return_to.startswith('/register'):
        return None

    # Limit length to prevent excessively long URLs
    if len(return_to) > 500:
        return None

    return return_to
```

### 2. Security Features

✅ **Prevent Open Redirects**: Only relative URLs allowed (e.g., `/account`, `/resources/page.html`)
✅ **Prevent Redirect Loops**: Reject `/login` and `/register` as destinations
✅ **Length Limiting**: Max 500 characters to prevent abuse
✅ **Input Sanitization**: Strip whitespace, normalize paths
✅ **Protocol Blocking**: Reject `http://`, `https://`, `//`, etc.

### 3. Updated Endpoints

#### Login Page (GET /login)
- Now sanitizes `return_to` before rendering template
- Passes only safe URLs to the login form

#### Login Handler (POST /login)
- Sanitizes `return_to` before redirecting
- Falls back to `/account` if `return_to` is invalid

#### Register Page (GET /register)
- Added `return_to` parameter support
- Sanitizes before rendering template

#### Register Handler (POST /register)
- Added `return_to` parameter to form
- Sanitizes before using in redirect
- Preserves safe `return_to` when redirecting to login after registration
- Error responses preserve sanitized `return_to`

### 4. Template Updates

#### `app/templates/register.html`
- Added hidden `return_to` field to form
- Updated "Login here" link to preserve `return_to` parameter

#### `app/templates/login.html`
- Already had `return_to` field support (no changes needed)

## Testing

Validated the `sanitize_return_to()` function with test cases:

| Input | Expected Output | Description |
|-------|----------------|-------------|
| `/login` | `None` | Reject /login |
| `/register` | `None` | Reject /register |
| `/login?return_to=/account` | `None` | Reject /login with params |
| `/account` | `/account` | Allow /account |
| `http://evil.com` | `None` | Reject external URL |
| `//evil.com` | `None` | Reject protocol-relative URL |
| `account` | `/account` | Add leading slash |
| `/resources/page.html` | `/resources/page.html` | Allow normal page |
| `  /account  ` | `/account` | Strip whitespace |
| `` (empty) | `None` | Reject empty |
| `/` + 600 chars | `None` | Reject too long |

**Result**: All 11 tests passed ✅

## Files Modified

1. **`app/auth.py`**
   - Added `sanitize_return_to()` function
   - Updated `GET /login` to sanitize `return_to`
   - Updated `POST /login` to sanitize `return_to` before redirect
   - Updated `GET /register` to accept and sanitize `return_to`
   - Updated `POST /register` to preserve sanitized `return_to`

2. **`app/templates/register.html`**
   - Added hidden `return_to` field to form
   - Updated "Login here" link to preserve `return_to`

## Deployment

1. **Built Docker image**: `192.168.2.1:5000/kevsrobots/chatter:latest`
2. **Pushed to registry**: `sha256:ec59c3f7c9dc65546e6c3976b7bf022995dc01e9d07a61a2752aa101f2c6d4c5`
3. **Ready for deployment**: Pull and restart containers on production servers

## Impact

### Before Fix
- Infinite redirect loops possible
- URLs could grow to thousands of characters
- Open redirect vulnerability
- 522 errors from slow/timeout requests
- Security risk (external redirects)

### After Fix
- Redirect loops prevented
- URLs limited to 500 characters
- Only internal redirects allowed
- Better performance
- Improved security

## Additional Benefits

- **Better UX**: Users can navigate between login/register without losing their intended destination
- **Security**: Prevents open redirect attacks
- **Performance**: Shorter URLs, faster processing
- **Monitoring**: Easier to track in logs

## Future Considerations

1. **Add rate limiting** to login/register endpoints (already exists for some)
2. **Log suspicious `return_to` attempts** for security monitoring
3. **Consider URL encoding/decoding** if special characters needed in future
4. **Add CSRF protection** if not already present (appears to be missing)

## Recommendation

Deploy this fix ASAP as it addresses:
- Security vulnerability (open redirects)
- Performance issue (infinite loops causing 522 errors)
- User experience problem (broken navigation)

This fix is backwards compatible and doesn't require database migrations.
