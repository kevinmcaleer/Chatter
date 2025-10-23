# Password Reset System

Complete guide to the one-time code password reset system.

## Overview

Chatter uses a one-time code system for password resets when users forget their passwords. This system does not require email verification and relies on admin-mediated identity verification.

**Key Features:**
- ✅ No email required
- ✅ Admin verifies user identity
- ✅ 8-character alphanumeric codes
- ✅ 24-hour expiration
- ✅ Single use only
- ✅ Case-insensitive

---

## User Flow

### Step 1: User Forgets Password

User realizes they cannot remember their password and cannot login.

**User Actions:**
- Contact administrator via phone, email, or in-person
- Provide identifying information for verification

---

### Step 2: Admin Generates Reset Code

Administrator verifies user identity and generates a reset code.

**Admin Actions:**
1. Login to https://chatter.kevsrobots.com/account
2. Click "Admin Panel" button
3. Find user in the user list
4. Click blue key icon (🔑) next to user's name
5. Confirm code generation
6. Note the 8-character code displayed
7. Securely communicate code to user

**Code Example:**
```
A3B7K9M2
```

**Code Characteristics:**
- Length: 8 characters
- Characters: A-Z (uppercase) and 0-9 (digits)
- Example: `A3B7K9M2`, `X7Y2K9B4`, `M8N3P1Q6`
- Case-insensitive when user enters it

---

### Step 3: User Receives Code

User receives the reset code from admin via secure channel.

**Secure Communication Channels:**
- ✅ Phone call
- ✅ SMS text message
- ✅ In-person
- ❌ Email (not recommended - insecure)
- ❌ Public chat (not recommended)

---

### Step 4: User Resets Password

User visits the password reset page and enters their information.

**User Actions:**
1. Visit https://chatter.kevsrobots.com/login
2. Click "Forgot your password?" link
3. Enter username
4. Enter 8-character reset code
5. Enter new password (minimum 8 characters)
6. Confirm new password
7. Click "Reset Password"
8. Redirected to login page
9. Login with new password

**Reset Form Fields:**
- Username (required)
- Reset Code (required, 8 characters)
- New Password (required, minimum 8 characters)
- Confirm Password (required, must match)

---

### Step 5: Code is Cleared

After successful password reset, the code is automatically cleared.

**Database Changes:**
```sql
UPDATE "user"
SET password_reset_code = NULL,
    code_expires_at = NULL,
    hashed_password = '$2b$12$...'  -- New password hash
WHERE username = 'johndoe';
```

---

## Technical Details

### Code Generation

**Algorithm:**
```python
import secrets
import string

alphabet = string.ascii_uppercase + string.digits  # A-Z, 0-9
reset_code = ''.join(secrets.choice(alphabet) for _ in range(8))
# Result: "A3B7K9M2"
```

**Security:**
- Uses `secrets` module (cryptographically secure)
- 36 possible characters per position
- Total combinations: 36^8 = 2,821,109,907,456 (2.8 trillion)
- Brute force is impractical within 24-hour window

---

### Code Storage

Codes are stored in the `user` table:

**Database Schema:**
```sql
ALTER TABLE "user"
ADD COLUMN password_reset_code VARCHAR,
ADD COLUMN code_expires_at TIMESTAMP;
```

**Example Data:**
```sql
INSERT INTO "user" (
  username,
  password_reset_code,
  code_expires_at
) VALUES (
  'johndoe',
  'A3B7K9M2',
  '2025-10-24 15:30:00'  -- 24 hours from generation
);
```

---

### Code Validation

**Validation Steps:**
1. User exists?
2. User has reset code?
3. Code matches (case-insensitive)?
4. Code not expired?
5. Password valid (length, match)?

**Validation Code:**
```python
# Check code matches (case-insensitive)
if user.password_reset_code.upper() != reset_code.upper():
    return error("Invalid reset code")

# Check code not expired
if user.code_expires_at < datetime.utcnow():
    return error("Reset code has expired")
```

---

### Code Expiration

**Expiration Time:** 24 hours from generation

**Calculation:**
```python
from datetime import datetime, timedelta

expires_at = datetime.utcnow() + timedelta(hours=24)
```

**Checking if Expired:**
```python
if user.code_expires_at < datetime.utcnow():
    # Code expired
    return error("Reset code has expired")
```

**Finding Expired Codes:**
```sql
SELECT username, password_reset_code, code_expires_at
FROM "user"
WHERE password_reset_code IS NOT NULL
  AND code_expires_at < NOW();
```

---

## API Endpoints

### Generate Reset Code (Admin Only)

**Endpoint:** `POST /admin/generate-reset-code/{user_id}`

**Authentication:** Required (admin only)

**Request:**
```http
POST /admin/generate-reset-code/5 HTTP/1.1
Host: chatter.kevsrobots.com
Cookie: access_token=Bearer eyJ...
```

**Success Response:**
```html
<!-- Admin panel page with alert -->
<div class="alert alert-info">
  <h5>Password Reset Code Generated</h5>
  <p><strong>User:</strong> johndoe</p>
  <p><strong>Code:</strong> <code>A3B7K9M2</code></p>
  <p>This code expires in 24 hours.</p>
</div>
```

**Error Responses:**
- User not found
- Database error

---

### Reset Password with Code

**GET Endpoint:** `GET /reset-password`

**Response:** HTML form

---

**POST Endpoint:** `POST /reset-password`

**Request:**
```http
POST /reset-password HTTP/1.1
Host: chatter.kevsrobots.com
Content-Type: application/x-www-form-urlencoded

username=johndoe&reset_code=A3B7K9M2&new_password=NewSecure123&confirm_password=NewSecure123
```

**Success Response:**
```http
HTTP/1.1 303 See Other
Location: /login?reset=success
```

**Error Responses:**
- "Invalid username or reset code"
- "Passwords do not match"
- "Password must be at least 8 characters long"
- "No reset code has been generated for this account"
- "Reset code has expired"

---

## Security Considerations

### Threat Model

**Threats Mitigated:**
- ✅ Forgotten passwords
- ✅ Unauthorized password resets (requires admin action)
- ✅ Brute force attacks (2.8 trillion combinations, 24-hour window)
- ✅ Code reuse (single use only)
- ✅ Expired code use (24-hour expiration)

**Threats Not Mitigated:**
- ❌ Admin account compromise (admin can generate codes)
- ❌ Insecure code communication (if sent via email)
- ❌ Social engineering (depends on admin verification)

---

### Best Practices

**For Admins:**

1. **Verify User Identity**
   - Require multiple forms of identification
   - Ask security questions
   - Verify via known contact information

2. **Secure Communication**
   - Use phone call or in-person
   - Avoid email or public channels
   - Read code clearly, spell if necessary

3. **Document Actions**
   - Note why code was generated
   - Record how identity was verified
   - Keep audit trail

4. **Monitor for Abuse**
   - Watch for excessive reset requests
   - Investigate unusual patterns
   - Review accountlog regularly

**For Users:**

1. **Protect Reset Code**
   - Don't share with others
   - Don't write down in insecure locations
   - Use immediately upon receipt

2. **Use Strong Password**
   - Minimum 8 characters
   - Mix of uppercase, lowercase, numbers
   - Avoid common patterns

3. **Verify Admin Contact**
   - Ensure you're speaking to real admin
   - Be cautious of impersonators
   - Use official contact channels

---

## Database Queries

### Find Users with Active Reset Codes

```sql
SELECT
  username,
  password_reset_code,
  code_expires_at,
  CASE
    WHEN code_expires_at < NOW() THEN 'Expired'
    ELSE 'Active'
  END as status
FROM "user"
WHERE password_reset_code IS NOT NULL
ORDER BY code_expires_at DESC;
```

### Find Recently Generated Codes

```sql
SELECT
  u.username,
  u.password_reset_code,
  u.code_expires_at,
  al.changed_at as generated_at,
  admin.username as generated_by
FROM "user" u
JOIN accountlog al ON u.id = al.user_id
JOIN "user" admin ON al.changed_by = admin.id
WHERE al.action = 'password_reset_code_generated'
  AND al.changed_at > NOW() - INTERVAL '7 days'
ORDER BY al.changed_at DESC;
```

### Clean Up Expired Codes

```sql
UPDATE "user"
SET password_reset_code = NULL,
    code_expires_at = NULL
WHERE password_reset_code IS NOT NULL
  AND code_expires_at < NOW();
```

---

## Troubleshooting

### Common Issues

**Issue:** "Invalid reset code"

**Causes:**
- Code typed incorrectly
- Code expired
- Code already used
- Username incorrect

**Solution:**
- Double-check code spelling
- Verify username is correct
- Request new code if expired
- Contact admin for assistance

---

**Issue:** "Reset code has expired"

**Cause:** More than 24 hours since code generation

**Solution:**
- Contact admin
- Request new reset code
- Use code within 24 hours

---

**Issue:** Code not working immediately after generation

**Cause:** Database replication delay (rare)

**Solution:**
- Wait 1-2 minutes
- Try again
- Contact admin if persists

---

**Issue:** Admin can't generate code

**Causes:**
- Not logged in as admin
- User doesn't exist
- Database error

**Solution:**
```sql
-- Verify admin status
SELECT username, type FROM "user" WHERE username = 'admin_username';

-- Verify user exists
SELECT username FROM "user" WHERE username = 'target_user';
```

---

## Monitoring & Maintenance

### Metrics to Track

1. **Code Generation Rate**
   - How many codes generated per day/week
   - Trend over time
   - Spikes might indicate problems

2. **Code Usage Rate**
   - How many codes actually used
   - Unused codes might indicate user confusion

3. **Code Expiration Rate**
   - How many codes expire unused
   - High rate might indicate process issues

4. **Time to Use**
   - How long between generation and use
   - Quick use is ideal

### Automated Cleanup

**Cron Job to Clean Expired Codes:**
```bash
#!/bin/bash
# Run daily at 2 AM

psql $DATABASE_URL << EOF
UPDATE "user"
SET password_reset_code = NULL,
    code_expires_at = NULL
WHERE password_reset_code IS NOT NULL
  AND code_expires_at < NOW();
EOF
```

---

## Future Enhancements

Potential improvements:

- [ ] **Email-based reset codes** - Send codes via email
- [ ] **SMS-based reset codes** - Send codes via text message
- [ ] **Self-service reset** - Users request codes themselves (with verification)
- [ ] **Configurable expiration** - Admin sets expiration time
- [ ] **Code format options** - Different code formats (PIN, phrase, etc.)
- [ ] **Rate limiting** - Limit code generation per user
- [ ] **Notification system** - Alert users when code is generated
- [ ] **Code history** - Track all codes generated for audit

---

## Comparison with Email Reset

| Feature | One-Time Code | Email Reset |
|---------|--------------|-------------|
| **Email Required** | No | Yes |
| **Setup Time** | None | Email configuration needed |
| **Speed** | Immediate | Depends on email delivery |
| **Security** | Admin verifies identity | Email security |
| **User Experience** | Contact admin first | Self-service |
| **Admin Involvement** | Required | Optional |
| **Best For** | Small user base, high security | Large user base, convenience |

---

## Related Documentation

- [ADMIN.md](ADMIN.md) - Admin features and workflows
- [AUTHENTICATION.md](AUTHENTICATION.md) - Authentication system
- [API.md](API.md) - API endpoints for password reset
- [DATABASE.md](DATABASE.md) - Database schema for reset codes
