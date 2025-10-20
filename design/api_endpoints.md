# Account Management API Documentation

## Base URL
All endpoints are prefixed with `/accounts`

## Authentication
Most endpoints require authentication via Bearer token in either:
- `Authorization` header: `Bearer <token>`
- `access_token` cookie (HttpOnly)

Admin endpoints require the user to have `type = 1` (admin privileges).

---

## Public Endpoints

### Register New Account
**POST** `/accounts/register`

Create a new user account.

**Request Body:**
```json
{
  "username": "string (required)",
  "firstname": "string (required)",
  "lastname": "string (required)",
  "date_of_birth": "datetime (optional)",
  "email": "email (required)",
  "password": "string (required)"
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "username": "johndoe",
  "firstname": "John",
  "lastname": "Doe",
  "date_of_birth": "1990-01-01T00:00:00",
  "email": "john@example.com",
  "status": "active",
  "type": 0,
  "created_at": "2025-10-20T14:00:00",
  "updated_at": "2025-10-20T14:00:00"
}
```

**Errors:**
- `400 Bad Request` - Username or email already registered

**Logging:** Creates account log with action "created"

---

## User Endpoints (Authentication Required)

### Get Current Account
**GET** `/accounts/me`

Retrieve the authenticated user's account information.

**Response:** `200 OK`
```json
{
  "id": 1,
  "username": "johndoe",
  "firstname": "John",
  "lastname": "Doe",
  "date_of_birth": "1990-01-01T00:00:00",
  "email": "john@example.com",
  "status": "active",
  "type": 0,
  "created_at": "2025-10-20T14:00:00",
  "updated_at": "2025-10-20T14:00:00"
}
```

---

### Update Account
**PATCH** `/accounts/me`

Update the authenticated user's account information. Only provided fields will be updated.

**Request Body:**
```json
{
  "firstname": "string (optional)",
  "lastname": "string (optional)",
  "date_of_birth": "datetime (optional)",
  "email": "email (optional)"
}
```

**Response:** `200 OK`
Returns updated user object.

**Errors:**
- `400 Bad Request` - Email already in use

**Logging:** Creates account log with action "updated" for each changed field

---

### Reset Password
**POST** `/accounts/reset-password`

Reset the authenticated user's password.

**Request Body:**
```json
{
  "old_password": "string (required)",
  "new_password": "string (required)"
}
```

**Response:** `200 OK`
```json
{
  "message": "Password reset successfully"
}
```

**Errors:**
- `400 Bad Request` - Incorrect old password

**Logging:** Creates account log with action "updated", field "password" (values redacted)

---

### Delete Account
**DELETE** `/accounts/me`

Delete the authenticated user's account.

**Response:** `200 OK`
```json
{
  "message": "Account deleted successfully"
}
```

**Logging:** Creates account log with action "deleted" before deletion

---

## Admin Endpoints (Admin Authentication Required)

All admin endpoints require `type = 1` (admin privileges).

### Update Account Status
**PATCH** `/accounts/admin/{user_id}/status`

Enable or disable a user account.

**Path Parameters:**
- `user_id` (integer) - ID of user to modify

**Request Body:**
```json
{
  "status": "active | inactive"
}
```

**Response:** `200 OK`
```json
{
  "message": "User account activated successfully"
}
```
or
```json
{
  "message": "User account deactivated successfully"
}
```

**Errors:**
- `400 Bad Request` - Invalid status value
- `403 Forbidden` - Not an admin user
- `404 Not Found` - User not found

**Logging:** Creates account log with action "activated" or "deactivated"

---

### Admin Reset Password
**POST** `/accounts/admin/{user_id}/reset-password`

Reset a user's password (admin privilege).

**Path Parameters:**
- `user_id` (integer) - ID of user to modify

**Request Body:**
```json
{
  "new_password": "string (required)"
}
```

**Response:** `200 OK`
```json
{
  "message": "Password reset successfully"
}
```

**Errors:**
- `403 Forbidden` - Not an admin user
- `404 Not Found` - User not found

**Logging:** Creates account log with action "updated", field "password" (values redacted)

---

### Admin Delete Account
**DELETE** `/accounts/admin/{user_id}`

Delete a user account (admin privilege).

**Path Parameters:**
- `user_id` (integer) - ID of user to delete

**Response:** `200 OK`
```json
{
  "message": "User account deleted successfully"
}
```

**Errors:**
- `400 Bad Request` - Cannot delete own account via admin endpoint
- `403 Forbidden` - Not an admin user
- `404 Not Found` - User not found

**Logging:** Creates account log with action "deleted" before deletion

---

## Account Logging

All account operations are logged to the `account_logs` table with the following information:
- **user_id** - User affected by the action
- **action** - Type of action (created, updated, activated, deactivated, deleted)
- **field_changed** - Specific field that was modified (for updates)
- **old_value** - Previous value (passwords are redacted)
- **new_value** - New value (passwords are redacted)
- **changed_by** - User ID who made the change
- **changed_at** - Timestamp of the change
- **ip_address** - IP address of the request
- **user_agent** - Browser/client information

---

## Common HTTP Status Codes

- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - Insufficient privileges
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation error
