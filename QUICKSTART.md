# Chatter - Quick Start Guide

## ✅ Your App is Ready to Test!

The server is currently running on **http://127.0.0.1:8001**

## 🚀 What's Available

### 1. Interactive API Documentation
- **Swagger UI:** http://127.0.0.1:8001/docs
- **ReDoc:** http://127.0.0.1:8001/redoc

### 2. Test User Created
Already created for you:
- **Username:** `demouser`
- **Password:** `demo123456`
- **Email:** `demo@example.com`

### 3. API Endpoints Working

Test them in the browser at http://127.0.0.1:8001/docs or use curl:

**Get Account Info:**
```bash
# Login first to get token
TOKEN=$(curl -s -X POST "http://127.0.0.1:8001/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=demouser&password=demo123456" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Get account details
curl -s -X GET "http://127.0.0.1:8001/accounts/me" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

## 📝 Next Steps

### Test the API Interactively

1. Open http://127.0.0.1:8001/docs
2. Click on any endpoint (e.g., `GET /accounts/me`)
3. Click "Try it out"
4. For protected endpoints:
   - First call `POST /auth/login` with demouser/demo123456
   - Copy the access_token
   - Click "Authorize" button at top of page
   - Enter: `Bearer YOUR_TOKEN_HERE`
5. Now try the protected endpoints!

### Test Registration

Create a new user:
```bash
curl -X POST "http://127.0.0.1:8001/accounts/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "firstname": "New",
    "lastname": "User",
    "email": "new@example.com",
    "password": "password123"
  }'
```

### Test Account Updates

```bash
# Get token first
TOKEN=$(curl -s -X POST "http://127.0.0.1:8001/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=demouser&password=demo123456" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Update account
curl -X PATCH "http://127.0.0.1:8001/accounts/me" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "firstname": "Updated",
    "lastname": "Name"
  }'
```

### Check the Database

```bash
# View users
sqlite3 data/database.db "SELECT id, username, firstname, lastname, email, status FROM user;"

# View account logs
sqlite3 data/database.db "SELECT user_id, action, field_changed, old_value, new_value, changed_at FROM accountlog;"
```

## 🔍 What Was Built

### Issue #27: Account Management API
- ✅ User registration with validation
- ✅ Login with JWT tokens
- ✅ Get/update account information
- ✅ Password reset
- ✅ Account deletion
- ✅ Admin endpoints (enable/disable, password reset, delete)
- ✅ Comprehensive logging (all actions logged to database)
- ✅ 100% test coverage (30 passing tests)

### Issue #28: Jekyll Pages with JavaScript
- ✅ Login page
- ✅ Registration page
- ✅ Password reset page
- ✅ Account details page (with dynamic data loading)
- ✅ Reusable JavaScript API module (`account-api.js`)

## 📂 File Locations

**API Code:**
- `app/accounts.py` - Account management endpoints
- `app/models.py` - Database models (User, AccountLog)
- `app/schemas.py` - Request/response schemas
- `app/main.py` - FastAPI application setup

**Tests:**
- `tests/test_accounts.py` - 30 comprehensive tests

**Jekyll Pages:**
- `pages/login.html`
- `pages/register.html`
- `pages/password-reset.html`
- `pages/account-details.html`
- `pages/assets/js/account-api.js`

**Database:**
- `data/database.db` - SQLite database
- Tables: user, accountlog, like, comment

**Documentation:**
- `pages/README.md` - Jekyll pages documentation
- `RUNNING.md` - Detailed running instructions
- `design/api_endpoints.md` - Complete API documentation
- `design/database.dbml` - Database schema documentation

## 🛑 Stop the Server

The server is running in the background. To stop it, press `Ctrl+C` in the terminal where it's running, or:

```bash
# Find the process
lsof -i :8001

# Kill it
kill <PID>
```

## 🔄 Restart the Server

```bash
./run_server.sh
# OR
uvicorn app.main:app --reload --port 8001
```

## ❓ Troubleshooting

**Port already in use?**
```bash
# Use a different port
uvicorn app.main:app --reload --port 8002
```

**Database schema errors?**
```bash
# Delete and recreate database
rm data/database.db
# Restart server - it will recreate with correct schema
```

**Need to reset?**
```bash
# Delete database and restart
rm data/database.db
./run_server.sh
```

## 🎯 All Features Working

- ✅ User registration
- ✅ Login/logout
- ✅ Get account info
- ✅ Update profile
- ✅ Password reset
- ✅ Account deletion
- ✅ Admin operations
- ✅ Account logging (all changes tracked)
- ✅ JWT authentication
- ✅ Form validation
- ✅ Error handling

**Enjoy testing Chatter!** 🎉
