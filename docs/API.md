# API Reference

Complete API documentation for Chatter authentication service.

## Base URL

**Production:** `https://chatter.kevsrobots.com`
**Local Development:** `http://localhost:8001`

## Authentication

Chatter uses JWT tokens stored in HTTP-only cookies. After successful login, two cookies are set:
- `access_token` - Secure JWT token (httponly, used for authentication)
- `username` - Non-httponly cookie (readable by JavaScript for UI purposes)

## Form-Based Endpoints (Web UI)

### User Registration

#### `GET /register`
Display registration form.

**Query Parameters:**
- `return_to` (optional) - URL to redirect to after successful registration

**Response:** HTML registration page

---

#### `POST /register`
Process user registration.

**Content-Type:** `application/x-www-form-urlencoded`

**Form Fields:**
- `username` (required) - Unique username
- `firstname` (required) - First name
- `lastname` (required) - Last name
- `email` (required) - Unique email address
- `password` (required) - Minimum 8 characters
- `date_of_birth` (optional) - Date of birth

**Success Response:** Redirect to `/login`

**Error Response:**
- HTML form with inline error messages
- Common errors: "Username already exists", "Email already registered"

**Example:**
```html
<form method="post" action="/register">
  <input type="text" name="username" required>
  <input type="text" name="firstname" required>
  <input type="text" name="lastname" required>
  <input type="email" name="email" required>
  <input type="password" name="password" required minlength="8">
  <input type="date" name="date_of_birth">
  <button type="submit">Register</button>
</form>
```

---

### User Login

#### `GET /login`
Display login form.

**Query Parameters:**
- `return_to` (optional) - URL to redirect to after successful login
- `reset` (optional) - Set to "success" to show password reset success message

**Response:** HTML login page

---

#### `POST /login`
Authenticate user and create session.

**Content-Type:** `application/x-www-form-urlencoded`

**Form Fields:**
- `username` (required) - Username
- `password` (required) - Password
- `return_to` (optional) - URL to redirect to after login

**Success Response:**
- Redirect to `return_to` URL or `/account` if not specified
- Sets cookies: `access_token`, `username`

**Error Response:** HTML form with error message "Invalid credentials"

**Rate Limiting:** 5 requests per minute per IP

**Example:**
```html
<form method="post" action="/login">
  <input type="text" name="username" required>
  <input type="password" name="password" required>
  <input type="hidden" name="return_to" value="https://www.kevsrobots.com/">
  <button type="submit">Login</button>
</form>
```

---

### Logout

#### `GET /logout`
End user session and clear cookies.

**Authentication:** Not required

**Response:** Redirect to `/login`

**Side Effects:** Clears `access_token` and `username` cookies

---

### Account Management

#### `GET /account`
Display user account page.

**Authentication:** Required (JWT cookie)

**Response:** HTML account page with:
- User profile information
- Account update form
- Password change form
- Activity statistics (likes, comments)
- Account deletion option
- Admin panel button (if user is admin)

---

#### `POST /account/update`
Update user email address.

**Authentication:** Required (JWT cookie)

**Content-Type:** `application/x-www-form-urlencoded`

**Form Fields:**
- `email` (required) - New email address

**Success Response:** Redirect to `/account` with success message

**Error Response:** HTML form with error message

**Note:** Username cannot be changed to prevent session invalidation

---

#### `POST /account/change-password`
Change user password.

**Authentication:** Required (JWT cookie)

**Content-Type:** `application/x-www-form-urlencoded`

**Form Fields:**
- `current_password` (required) - Current password for verification
- `new_password` (required) - New password (minimum 8 characters)

**Success Response:** Redirect to `/account` with success message

**Error Response:** HTML form with error message

---

#### `POST /account/delete`
Delete user account.

**Authentication:** Required (JWT cookie)

**Confirmation:** Requires JavaScript confirmation dialog

**Success Response:** Redirect to `/login`

**Side Effects:**
- Deletes user account and all associated data (cascading delete)
- Clears authentication cookies
- Logs account deletion in audit log

---

### Password Reset

#### `GET /reset-password`
Display password reset form.

**Authentication:** Not required

**Response:** HTML password reset page

---

#### `POST /reset-password`
Reset password using one-time code.

**Content-Type:** `application/x-www-form-urlencoded`

**Form Fields:**
- `username` (required) - Username
- `reset_code` (required) - 8-character code from admin
- `new_password` (required) - New password (minimum 8 characters)
- `confirm_password` (required) - Password confirmation

**Success Response:** Redirect to `/login?reset=success`

**Error Responses:**
- "Invalid username or reset code"
- "Passwords do not match"
- "Password must be at least 8 characters long"
- "No reset code has been generated for this account"
- "Reset code has expired"

**Side Effects:**
- Updates user password
- Clears `password_reset_code` and `code_expires_at` fields

---

## Admin Endpoints

All admin endpoints require authentication with admin user (type=1).

### Admin Panel

#### `GET /admin`
Display admin user management panel.

**Authentication:** Required (admin only)

**Response:** HTML admin panel with:
- List of all users
- User details (username, name, email, type, status, last login, created date)
- Password reset code indicator badges
- Action buttons for each user

---

#### `POST /admin/generate-reset-code/{user_id}`
Generate one-time password reset code for a user.

**Authentication:** Required (admin only)

**Path Parameters:**
- `user_id` (integer) - ID of user to generate code for

**Success Response:**
- HTML admin panel with success alert
- Displays generated 8-character code (e.g., `A3B7K9M2`)
- Code visible to admin for secure communication to user

**Error Responses:**
- "User not found"

**Side Effects:**
- Sets `password_reset_code` on user
- Sets `code_expires_at` to 24 hours from now

**Example Code:**
```
Code: A3B7K9M2
Expires: 24 hours
```

---

#### `POST /admin/force-password-reset/{user_id}`
Force user to reset password on next login.

**Authentication:** Required (admin only)

**Path Parameters:**
- `user_id` (integer) - ID of user to force reset

**Success Response:** HTML admin panel with success message

**Error Responses:**
- "User not found"
- "Cannot force password reset on yourself"

**Side Effects:** Sets `force_password_reset=true` on user

---

### Forced Password Reset

#### `GET /force-password-reset`
Display forced password reset page (shown when user has force_password_reset flag).

**Authentication:** Required (JWT cookie)

**Response:** HTML password reset form

**Note:** User is automatically redirected here on login if `force_password_reset=true`

---

#### `POST /force-password-reset`
Handle forced password reset submission.

**Authentication:** Required (JWT cookie)

**Content-Type:** `application/x-www-form-urlencoded`

**Form Fields:**
- `new_password` (required) - New password (minimum 8 characters)
- `confirm_password` (required) - Password confirmation

**Success Response:** Redirect to `/account`

**Error Responses:**
- "Passwords do not match"
- "Password must be at least 8 characters long"

**Side Effects:**
- Updates user password
- Clears `force_password_reset` flag

---

## JSON API Endpoints (Deprecated)

These endpoints are maintained for backward compatibility but are deprecated in favor of form-based endpoints.

### Register User (API)

#### `POST /api/register`
Register new user via JSON API.

**Deprecated:** Use `POST /register` instead

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "username": "johndoe",
  "firstname": "John",
  "lastname": "Doe",
  "email": "john@example.com",
  "password": "SecurePass123",
  "date_of_birth": "1990-01-01"
}
```

**Success Response:** `201 Created`
```json
{
  "id": 1,
  "username": "johndoe",
  "firstname": "John",
  "lastname": "Doe",
  "email": "john@example.com",
  "status": "active",
  "type": 0,
  "created_at": "2025-10-23T12:00:00"
}
```

**Rate Limiting:** 3 requests per hour per IP

---

### Login (API)

#### `POST /api/login`
Authenticate via JSON API using OAuth2 password flow.

**Content-Type:** `application/x-www-form-urlencoded`

**Form Fields:**
- `username` (required) - Username
- `password` (required) - Password

**Success Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Error Response:** `401 Unauthorized`
```json
{
  "detail": "Invalid credentials"
}
```

**Rate Limiting:** 5 requests per minute per IP

---

## Health Check

#### `GET /health`
Health check endpoint for monitoring.

**Authentication:** Not required

**Response:** `200 OK`
```json
{
  "status": "healthy"
}
```

---

## Error Responses

All form-based endpoints return HTML with inline error messages.
JSON API endpoints return standard HTTP error codes:

- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

---

## Rate Limiting

Rate limits are applied to prevent abuse:

| Endpoint | Limit | Window |
|----------|-------|--------|
| `POST /login` | 5 requests | 1 minute |
| `POST /api/login` | 5 requests | 1 minute |
| `POST /register` | 3 requests | 1 hour |
| `POST /api/register` | 3 requests | 1 hour |

When rate limit is exceeded, you'll receive a `429 Too Many Requests` response.

---

## CORS Configuration

CORS is configured to allow requests from:
- `http://localhost:4000` (local development)
- `http://local.kevsrobots.com:4000` (local development)
- `https://www.kevsrobots.com` (production)
- `https://kevsrobots.com` (production)

Credentials (cookies) are allowed for cross-origin requests.

---

## Interactive API Documentation

FastAPI provides interactive API documentation:

- **Swagger UI:** https://chatter.kevsrobots.com/docs
- **ReDoc:** https://chatter.kevsrobots.com/redoc
