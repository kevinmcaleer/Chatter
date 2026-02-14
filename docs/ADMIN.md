# Admin Features

Documentation for administrative features in Chatter.

## Overview

Chatter includes an admin panel for managing users, generating password reset codes, and viewing user activity. Admin features are only accessible to users with `type=1`.

**Admin Panel URL:** https://chatter.kevsrobots.com/admin

## Becoming an Admin

### Creating the First Admin

1. Register a regular user account
2. Connect to the database
3. Update user type to admin:

```sql
UPDATE "user" SET type = 1 WHERE username = 'admin_username';
```

### Verifying Admin Status

```sql
SELECT username, email, type FROM "user" WHERE type = 1;
```

---

## Admin Panel

### Accessing the Admin Panel

**URL:** `/admin`

**Requirements:**
- Must be logged in
- User type must be 1 (admin)

**Access from Account Page:**
- Admin users see an "Admin Panel" button in the top right of their account page
- Click button to access admin panel

### Panel Features

The admin panel displays a comprehensive user management table with:

#### User Information Columns

| Column | Description |
|--------|-------------|
| **Username** | User's unique username with badges |
| **Name** | Full name (first + last) |
| **Email** | Email address |
| **Type** | Badge showing "Admin" (red) or "User" (gray) |
| **Status** | Badge showing "Active" (green) or "Inactive" (gray) |
| **Last Login** | Timestamp of last successful login or "Never" |
| **Created** | Account creation date |
| **Actions** | Buttons for admin actions |

#### User Badges

**Password Reset Required:**
- Yellow warning badge with key icon
- Shown when `force_password_reset = true`
- Indicates user must reset password on next login

**Example User Row:**
```
┌────────────┬──────────┬──────────────────┬───────┬────────┬─────────────────┬────────────┬─────────┐
│ Username   │ Name     │ Email            │ Type  │ Status │ Last Login      │ Created    │ Actions │
├────────────┼──────────┼──────────────────┼───────┼────────┼─────────────────┼────────────┼─────────┤
│ johndoe ⚠️ │ John Doe │ john@example.com │ User  │ Active │ 2025-10-23 15:30│ 2025-10-20 │ 🔑 🔒   │
└────────────┴──────────┴──────────────────┴───────┴────────┴─────────────────┴────────────┴─────────┘
```

---

## Admin Actions

### 1. Generate Password Reset Code

**Button:** Blue key icon (🔑)

**Purpose:** Generate a one-time code for users who forgot their password

**Flow:**
1. Admin clicks blue key icon for a user
2. Confirmation dialog: "Generate a reset code for {username}?"
3. Admin confirms
4. System generates 8-character alphanumeric code
5. Code displayed in large alert box at top of page
6. Admin communicates code to user securely

**Generated Code Display:**
```
┌─────────────────────────────────────────────────────────┐
│ 🔑 Password Reset Code Generated                        │
│                                                          │
│ User: johndoe                                           │
│ Code: A3B7K9M2                                          │
│ ─────────────────────────────────────────────────────   │
│ ⏰ This code expires in 24 hours.                       │
│ ⚠️  Give this code to the user securely.                │
└─────────────────────────────────────────────────────────┘
```

**Technical Details:**
- Code length: 8 characters
- Characters: Uppercase letters (A-Z) + digits (0-9)
- Expiration: 24 hours from generation
- Single use: Code is cleared after successful password reset
- Case-insensitive: User can enter lowercase

**Database Changes:**
```sql
UPDATE "user"
SET password_reset_code = 'A3B7K9M2',
    code_expires_at = NOW() + INTERVAL '24 hours'
WHERE id = {user_id};
```

**Endpoint:** `POST /admin/generate-reset-code/{user_id}`

---

### 2. Force Password Reset on Next Login

**Button:** Yellow lock icon (🔒)

**Purpose:** Require user to change password when they next login

**Flow:**
1. Admin clicks yellow lock icon for a user
2. Confirmation dialog: "Force {username} to reset their password on next login?"
3. Admin confirms
4. User's account flagged for password reset
5. Yellow warning badge appears next to username
6. When user logs in, they're redirected to password reset page

**Use Cases:**
- Security concern (potential compromise)
- Password policy change
- User requested password assistance
- Account recovery

**Technical Details:**
- Sets `force_password_reset = true` on user
- User cannot access account until password is reset
- Password reset page displayed automatically on login
- Flag cleared after successful password reset

**Database Changes:**
```sql
UPDATE "user"
SET force_password_reset = true
WHERE id = {user_id};
```

**Endpoint:** `POST /admin/force-password-reset/{user_id}`

**Restrictions:**
- Cannot force password reset on yourself
- Error shown if attempted

---

## Admin Workflows

### Password Reset Workflow (Recommended)

**When user forgets password:**

1. User contacts admin (phone, email, in-person)
2. Admin verifies user identity
3. Admin logs into admin panel
4. Admin finds user in list
5. Admin clicks **blue key icon** (🔑)
6. Admin notes the 8-character code
7. Admin communicates code to user securely
8. User visits `/reset-password`
9. User enters username + code + new password
10. User logs in with new password

**Advantages:**
- ✅ No email required
- ✅ Immediate resolution
- ✅ Code expires automatically
- ✅ Single use only
- ✅ Admin verifies identity first

---

### Force Password Reset Workflow

**When password change is required:**

1. Admin logs into admin panel
2. Admin finds user in list
3. Admin clicks **yellow lock icon** (🔒)
4. Admin confirms action
5. Admin notifies user password reset is required
6. User logs in (redirected to reset page automatically)
7. User changes password
8. User can access account normally

**Advantages:**
- ✅ User-initiated password change
- ✅ No admin involvement in new password
- ✅ Enforced security policy
- ✅ User experience is seamless

---

## Admin Security

### Access Control

**Admin Check Dependency:**
```python
def get_current_admin(current_user: User = Depends(get_current_user)):
    """Verify user is an admin"""
    if current_user.type != 1:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    return current_user
```

**Protected Routes:**
- GET `/admin` - Admin panel
- POST `/admin/generate-reset-code/{user_id}` - Generate reset code
- POST `/admin/force-password-reset/{user_id}` - Force password reset

**Error Response (Non-Admin):**
```
HTTP 403 Forbidden
{
  "detail": "Admin access required"
}
```

### Admin Best Practices

1. **Limit Admin Accounts**
   - Only create admin accounts for trusted personnel
   - Review admin list regularly

2. **Verify User Identity**
   - Before generating reset codes, verify the user's identity
   - Use secondary authentication (phone, email, in-person)

3. **Communicate Codes Securely**
   - Don't send codes via email (insecure)
   - Use phone call, SMS, or in-person
   - Verify you're speaking to the correct person

4. **Monitor Admin Actions**
   - Review `accountlog` table for admin actions
   - Look for unusual patterns

5. **Protect Admin Credentials**
   - Use strong, unique passwords
   - Don't share admin accounts
   - Consider 2FA (future enhancement)

6. **Document Admin Actions**
   - Keep record of why password resets were generated
   - Note user verification method used

---

## Admin Audit Trail

All admin actions are logged to the `accountlog` table:

**Generate Reset Code:**
```sql
INSERT INTO accountlog (
  user_id,
  action,
  field_changed,
  new_value,
  changed_by,
  changed_at,
  ip_address
) VALUES (
  5,                           -- User who received reset code
  'password_reset_code_generated',
  'password_reset_code',
  'A3B7K9M2',                  -- The generated code
  1,                           -- Admin who generated it
  NOW(),
  '192.168.1.100'
);
```

**Force Password Reset:**
```sql
INSERT INTO accountlog (
  user_id,
  action,
  field_changed,
  old_value,
  new_value,
  changed_by,
  changed_at,
  ip_address
) VALUES (
  5,                           -- User who was flagged
  'force_password_reset',
  'force_password_reset',
  'false',
  'true',
  1,                           -- Admin who set the flag
  NOW(),
  '192.168.1.100'
);
```

### Querying Admin Actions

**All admin actions:**
```sql
SELECT
  u.username as affected_user,
  al.action,
  al.field_changed,
  al.old_value,
  al.new_value,
  admin.username as admin_user,
  al.changed_at,
  al.ip_address
FROM accountlog al
JOIN "user" u ON al.user_id = u.id
JOIN "user" admin ON al.changed_by = admin.id
WHERE admin.type = 1  -- Admin users only
ORDER BY al.changed_at DESC;
```

**Recent password reset codes:**
```sql
SELECT
  u.username,
  al.new_value as reset_code,
  al.changed_at as generated_at,
  admin.username as generated_by
FROM accountlog al
JOIN "user" u ON al.user_id = u.id
JOIN "user" admin ON al.changed_by = admin.id
WHERE al.action = 'password_reset_code_generated'
  AND al.changed_at > NOW() - INTERVAL '7 days'
ORDER BY al.changed_at DESC;
```

---

## Admin Panel UI

### Alerts & Messages

**Success Alert (Green):**
- Shown after successful action
- Example: "Reset code generated for johndoe"
- Auto-dismissible

**Error Alert (Red):**
- Shown when action fails
- Example: "User not found", "Cannot force password reset on yourself"
- Auto-dismissible

**Info Alert (Blue):**
- Shown when reset code is generated
- Displays the code prominently
- Includes expiration warning
- Auto-dismissible

### Responsive Design

The admin panel is fully responsive:
- **Desktop:** Full table with all columns
- **Tablet:** Horizontally scrollable table
- **Mobile:** Scrollable table, stacked on small screens

### Icons & Visual Indicators

| Icon | Color | Meaning |
|------|-------|---------|
| 🔑 (key) | Blue | Generate reset code |
| 🔒 (lock) | Yellow | Force password reset |
| ⚠️ (warning) | Yellow | Password reset required |
| 👨‍💼 (admin) | Red badge | Admin user |
| 👤 (user) | Gray badge | Regular user |
| ✅ (check) | Green badge | Active account |
| ⭕ (circle) | Gray badge | Inactive account |

---

## Future Enhancements

Potential admin features for future development:

- [ ] **Account Activation/Deactivation** - Toggle user status
- [ ] **User Impersonation** - Login as user (with audit trail)
- [ ] **Bulk Actions** - Reset passwords for multiple users
- [ ] **User Search/Filter** - Find users by name, email, etc.
- [ ] **Activity Dashboard** - Charts showing logins, registrations
- [ ] **Email Notifications** - Send password reset emails
- [ ] **2FA Management** - Require/reset 2FA for users
- [ ] **Account Merging** - Combine duplicate accounts
- [ ] **Ban/Unban Users** - Prevent access (more than inactive)
- [ ] **Admin Activity Log** - Dedicated page for admin actions
- [ ] **Export User Data** - CSV export of user list

---

## Troubleshooting

### Common Issues

**Issue:** "Admin access required" error

**Cause:** User type is not 1

**Solution:**
```sql
-- Check user type
SELECT username, type FROM "user" WHERE username = 'your_username';

-- Update to admin
UPDATE "user" SET type = 1 WHERE username = 'your_username';
```

---

**Issue:** Reset code not generating

**Cause:** Database error or constraint violation

**Solution:**
- Check database logs
- Verify user exists
- Ensure columns exist (run migration 004)

---

**Issue:** Admin button not visible on account page

**Cause:** User type not set to admin

**Solution:**
```sql
UPDATE "user" SET type = 1 WHERE username = 'your_username';
```

Then refresh the page.

---

## Security Considerations

### Admin Account Security

1. **Strong Passwords Required**
   - Minimum 8 characters
   - Mix of uppercase, lowercase, numbers
   - Consider special characters

2. **Limit Admin Access**
   - Only grant to trusted personnel
   - Review admin list monthly
   - Remove admin access when no longer needed

3. **Monitor Admin Activity**
   - Review accountlog regularly
   - Look for unusual patterns
   - Investigate unexpected actions

4. **Secure Reset Code Communication**
   - Never send codes via unsecured channels
   - Verify user identity before generating codes
   - Use phone or in-person communication

5. **Regular Security Audits**
   - Review admin actions monthly
   - Check for dormant admin accounts
   - Verify admin accounts still needed

---

## Support

For admin-related questions:
- Check this documentation first
- Review [API.md](API.md) for endpoint details
- Submit GitHub issue if problem persists
- Contact system administrator

Remember: **With great power comes great responsibility!** Admin access should be used carefully and ethically.
