# Running Chatter Locally

Quick guide to run and test the Chatter application locally.

## Quick Start

### Option 1: Using the Run Script (Easiest)

```bash
./run_server.sh
```

This will:
- Activate the virtual environment
- Install dependencies if needed
- Start the FastAPI server on http://127.0.0.1:8000

### Option 2: Manual Start

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload
```

## What You'll Get

Once the server is running, you'll have access to:

### 1. API Endpoints
**Base URL:** http://127.0.0.1:8000

**Documentation:**
- Interactive API Docs (Swagger): http://127.0.0.1:8000/docs
- Alternative Docs (ReDoc): http://127.0.0.1:8000/redoc

**Main Endpoints:**
- `POST /accounts/register` - Create new account
- `POST /auth/login` - Login with username/password
- `GET /accounts/me` - Get current user info (requires auth)
- `PATCH /accounts/me` - Update account (requires auth)
- `POST /accounts/reset-password` - Reset password (requires auth)
- `DELETE /accounts/me` - Delete account (requires auth)
- `PATCH /accounts/admin/{user_id}/status` - Enable/disable accounts (admin)
- `POST /accounts/admin/{user_id}/reset-password` - Admin password reset
- `DELETE /accounts/admin/{user_id}` - Delete user (admin)

### 2. Existing HTML Templates (Jinja2)
- http://127.0.0.1:8000/auth/login
- http://127.0.0.1:8000/auth/register
- http://127.0.0.1:8000/auth/account

### 3. Database
- SQLite database: `data/database.db`
- Tables: `user`, `accountlog`, `like`, `comment`

## Testing the API

### Option 1: Use the Test Script

```bash
./test_api.sh
```

This automated script will:
- Register a test user
- Login and get a token
- Retrieve account information
- Update the account
- Verify logging is working

### Option 2: Use the Interactive API Docs

1. Open http://127.0.0.1:8000/docs
2. Try the `/accounts/register` endpoint:
   - Click "Try it out"
   - Fill in the example data
   - Click "Execute"
3. Then try `/auth/login` to get a token
4. Click "Authorize" button at the top
5. Enter: `Bearer YOUR_TOKEN_HERE`
6. Now you can test authenticated endpoints

### Option 3: Use curl

**Register:**
```bash
curl -X POST "http://127.0.0.1:8000/accounts/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "firstname": "John",
    "lastname": "Doe",
    "email": "john@example.com",
    "password": "password123"
  }'
```

**Login:**
```bash
curl -X POST "http://127.0.0.1:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=johndoe&password=password123"
```

**Get Account (replace TOKEN):**
```bash
curl -X GET "http://127.0.0.1:8000/accounts/me" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Testing the Jekyll Pages

The Jekyll pages in `pages/` are static files that need to be served separately:

### Option 1: Simple Python Server

```bash
# In a new terminal (keep FastAPI server running)
cd pages
python -m http.server 8080
```

Then open:
- http://127.0.0.1:8080/login.html
- http://127.0.0.1:8080/register.html
- http://127.0.0.1:8080/password-reset.html
- http://127.0.0.1:8080/account-details.html

**Note:** The JavaScript will connect to the API at http://127.0.0.1:8000

### Option 2: Use with Jekyll

If you have Jekyll installed:

```bash
cd pages
jekyll serve
```

Then open http://127.0.0.1:4000

## Checking the Database

### View Database Tables

```bash
sqlite3 data/database.db "SELECT * FROM user;"
sqlite3 data/database.db "SELECT * FROM accountlog;"
```

### View Logs for a User

```bash
sqlite3 data/database.db "SELECT * FROM accountlog WHERE user_id = 1;"
```

### Check Log Count

```bash
sqlite3 data/database.db "SELECT COUNT(*) FROM accountlog;"
```

## Troubleshooting

### Port Already in Use

If port 8000 is busy, use a different port:

```bash
uvicorn app.main:app --reload --port 8001
```

Then update the API URL in your tests to http://127.0.0.1:8001

### Database Not Found

The database is created automatically on first run at `data/database.db`. If you want to reset it:

```bash
rm data/database.db
# Restart the server - it will recreate the database
```

### Secret Key Error

If you see "SECRET_KEY not set", check that `app/.env` exists with:

```
SECRET_KEY = "593cfcf727eb333e24c83a661f8790dd551aa72bf02a72d355810d36ad8fa8db"
```

### CORS Issues with Jekyll Pages

If you get CORS errors when testing Jekyll pages, you may need to add CORS middleware. The API currently runs on the same origin, so this shouldn't be an issue.

## Development Workflow

**Recommended setup for testing:**

1. **Terminal 1:** Run FastAPI server
   ```bash
   ./run_server.sh
   ```

2. **Terminal 2:** Run tests or serve static pages
   ```bash
   ./test_api.sh
   # OR
   cd pages && python -m http.server 8080
   ```

3. **Browser:**
   - API Docs: http://127.0.0.1:8000/docs
   - Static Pages: http://127.0.0.1:8080/login.html

## Running Tests

```bash
# Run all tests
pytest tests/test_accounts.py -v

# Run with coverage
pytest tests/test_accounts.py --cov=app/accounts --cov-report=term-missing

# Run specific test
pytest tests/test_accounts.py::TestRegistration::test_register_success -v
```

## Stopping the Server

Press `Ctrl+C` in the terminal where the server is running.

## Next Steps

After testing locally:
1. Create admin user (type=1) for testing admin endpoints
2. Test all account management features
3. Verify account logging in database
4. Test Jekyll pages with the API
5. Run the full test suite

## Environment Variables

Current configuration (from `app/.env`):
- `SECRET_KEY` - JWT token signing key
- Database: SQLite at `data/database.db`

## Default Test User

After running `test_api.sh`, you'll have:
- Username: `testuser`
- Password: `password123`
- Email: `test@example.com`

You can use this to login and test the UI!
