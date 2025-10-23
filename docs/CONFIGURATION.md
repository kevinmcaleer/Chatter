# Configuration Guide

Complete guide to configuring Chatter for different environments.

## Environment Variables

Chatter is configured via environment variables stored in a `.env` file.

### Required Variables

```bash
# Database Connection
DATABASE_URL=postgresql://username:password@host:port/database

# JWT Secret Key (generate with: openssl rand -hex 32)
SECRET_KEY=your-secret-key-here-64-characters-minimum
```

### Optional Variables

```bash
# Environment Mode
ENVIRONMENT=production  # or 'development'

# CORS Allowed Origins (comma-separated)
ALLOWED_ORIGINS=https://www.kevsrobots.com,https://kevsrobots.com

# Server Settings
HOST=0.0.0.0
PORT=8006
```

---

## Environment Modes

### Production

**Settings:**
```bash
ENVIRONMENT=production
```

**Behavior:**
- Cookies use `Secure` flag (HTTPS only)
- Cookies use domain `.kevsrobots.com`
- Database connection pooling enabled
- SQL echo disabled
- Debug mode disabled

**Example .env:**
```bash
DATABASE_URL=postgresql://user:pass@192.168.2.3:5433/kevsrobots_cms
SECRET_KEY=abc123def456...
ENVIRONMENT=production
ALLOWED_ORIGINS=https://www.kevsrobots.com,https://kevsrobots.com
```

---

### Development

**Settings:**
```bash
ENVIRONMENT=development
# or leave ENVIRONMENT unset
```

**Behavior:**
- Cookies don't use `Secure` flag (HTTP allowed)
- Cookies don't use domain restriction
- SQL echo enabled (query logging)
- Debug mode enabled
- Smaller connection pool

**Example .env:**
```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/chatter_dev
SECRET_KEY=dev-secret-key-not-for-production
ENVIRONMENT=development
ALLOWED_ORIGINS=http://localhost:4000,http://127.0.0.1:4000
```

---

## Database Configuration

### PostgreSQL Connection String

**Format:**
```
postgresql://username:password@host:port/database
```

**Components:**
- `username` - PostgreSQL user
- `password` - User password
- `host` - Database server hostname/IP
- `port` - PostgreSQL port (default 5432)
- `database` - Database name

**Production Example:**
```bash
DATABASE_URL=postgresql://chatter_user:SecurePass123@192.168.2.3:5433/kevsrobots_cms
```

**Development Example:**
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/chatter_dev
```

### Connection Pool Settings

Configured in `app/database.py`:

**Production:**
```python
pool_size=5          # Maintain 5 connections
max_overflow=10      # Allow 10 additional connections
pool_pre_ping=True   # Verify connections before use
pool_recycle=3600    # Recycle connections after 1 hour
echo=False          # Don't log SQL queries
```

**Development:**
```python
pool_size=2          # Smaller pool for dev
max_overflow=3
pool_pre_ping=True
pool_recycle=3600
echo=True           # Log all SQL queries
```

---

## Secret Key Generation

### Generating a Secure Key

**Using OpenSSL:**
```bash
openssl rand -hex 32
```

**Using Python:**
```python
import secrets
print(secrets.token_hex(32))
```

**Requirements:**
- Minimum 32 bytes (64 hex characters)
- Cryptographically secure random
- Keep secret - never commit to git

### Rotating Secret Keys

**Important:** Rotating the secret key invalidates all existing JWT tokens.

**Process:**
1. Generate new secret key
2. Update `.env` file
3. Restart application
4. All users must login again

---

## CORS Configuration

### Allowed Origins

Controls which domains can make cross-origin requests to Chatter.

**Format:**
```bash
ALLOWED_ORIGINS=origin1,origin2,origin3
```

**Production Example:**
```bash
ALLOWED_ORIGINS=https://www.kevsrobots.com,https://kevsrobots.com
```

**Development Example:**
```bash
ALLOWED_ORIGINS=http://localhost:4000,http://local.kevsrobots.com:4000
```

### CORS Settings

**Middleware Configuration:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Allow Credentials:**
- Enables cookies to be sent cross-origin
- Required for authentication to work
- Set to `True`

---

## Cookie Configuration

### Production Cookies

**Settings:**
```python
httponly=True      # Prevent JavaScript access (security)
secure=True        # HTTPS only
samesite="lax"     # CSRF protection
domain=".kevsrobots.com"  # Share across subdomains
max_age=1800       # 30 minutes
```

### Development Cookies

**Settings:**
```python
httponly=True      # Still prevent JavaScript access
secure=False       # Allow HTTP
samesite="lax"
domain=None        # Don't share across domains
max_age=1800
```

---

## Rate Limiting

### Configuration

Rate limits are applied per IP address.

**Settings in `app/auth.py`:**
```python
@limiter.limit("5/minute")
def login_user(...):
    # Login endpoint

@limiter.limit("3/hour")
def register_user(...):
    # Registration endpoint
```

### Customization

**Change Limits:**
```python
# app/auth.py

@router.post("/login")
@limiter.limit("10/minute")  # Increase to 10 per minute
def login_user(...):
    pass
```

**Disable in Testing:**
```python
if ENVIRONMENT != "production":
    limiter.enabled = False
```

---

## Server Configuration

### Host & Port

**Default:**
```bash
HOST=0.0.0.0
PORT=8006
```

**Custom:**
```bash
# Listen on specific interface
HOST=192.168.1.100
PORT=8080
```

### Running the Server

**Production (Docker):**
```bash
docker-compose up -d
```

**Development:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

**Production (Direct):**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8006 --workers 4
```

---

## File Structure

### Configuration Files

```
chatter/
├── .env                 # Environment variables (DO NOT COMMIT)
├── .env.example         # Template for .env
├── .env.docker          # Docker-specific template
├── .gitignore           # Excludes .env from git
├── requirements.txt     # Python dependencies
├── docker-compose.yml   # Docker configuration
└── Dockerfile           # Docker image definition
```

### Example .env File

**DO NOT COMMIT THIS FILE!**

```bash
# chatter/.env
# Local environment variables

# Database
DATABASE_URL=postgresql://chatter_user:SecurePass123@192.168.2.3:5433/kevsrobots_cms

# JWT Secret
SECRET_KEY=abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567890abcdef12

# Environment
ENVIRONMENT=production

# CORS
ALLOWED_ORIGINS=https://www.kevsrobots.com,https://kevsrobots.com

# Server
HOST=0.0.0.0
PORT=8006
```

### .env.example Template

**Safe to commit:**

```bash
# chatter/.env.example
# Copy to .env and fill in your values

# Database
DATABASE_URL=postgresql://username:password@host:port/database

# JWT Secret (generate with: openssl rand -hex 32)
SECRET_KEY=your-secret-key-here

# Environment (production or development)
ENVIRONMENT=production

# CORS (comma-separated list of allowed origins)
ALLOWED_ORIGINS=https://www.example.com

# Server
HOST=0.0.0.0
PORT=8006
```

---

## Docker Configuration

### docker-compose.yml

**Location:** `docker-compose.yml`

**Key Settings:**
```yaml
services:
  app:
    env_file:
      - .env  # Load environment variables from .env
    build:
      context: .
      dockerfile: Dockerfile
      pull: true
      args:
        - CACHEBUST=${CACHEBUST:-1}  # Force rebuild
    image: 192.168.2.1:5000/kevsrobots/chatter:latest
    ports:
      - "8006:8006"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8006/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Building Docker Image

**Local Build:**
```bash
docker-compose build
```

**Force Rebuild:**
```bash
CACHEBUST=$(date +%s) docker-compose build
```

**Push to Registry:**
```bash
docker-compose push
```

---

## Logging Configuration

### Application Logs

**Location:** Console output (captured by Docker)

**View Logs:**
```bash
# Docker logs
docker logs chatter-app

# Follow logs
docker logs -f chatter-app

# Last 100 lines
docker logs --tail 100 chatter-app
```

### Database Query Logging

**Enable in Development:**
```python
# app/database.py
echo = ENVIRONMENT != "production"
```

**Disable in Production:**
```python
echo = False
```

---

## Security Configuration

### Password Requirements

**Current Requirements:**
- Minimum 8 characters
- No complexity requirements (yet)

**Enforce in Code:**
```python
# app/schemas.py
minlength=8
```

**Future Enhancement:**
```python
# Add complexity requirements
import re

def validate_password(password: str) -> bool:
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):  # Uppercase
        return False
    if not re.search(r"[a-z]", password):  # Lowercase
        return False
    if not re.search(r"[0-9]", password):  # Number
        return False
    return True
```

### Session Timeout

**Current:** 30 minutes

**Configure:**
```python
# app/utils.py
def create_access_token(data: dict):
    expire = datetime.utcnow() + timedelta(minutes=30)  # Change here
```

---

## Environment-Specific Configuration

### Local Development

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/chatter_dev
SECRET_KEY=dev-secret-not-secure
ENVIRONMENT=development
ALLOWED_ORIGINS=http://localhost:4000
```

### Staging

```bash
DATABASE_URL=postgresql://user:pass@staging-db:5432/chatter_staging
SECRET_KEY=staging-secret-key-here
ENVIRONMENT=production
ALLOWED_ORIGINS=https://staging.kevsrobots.com
```

### Production

```bash
DATABASE_URL=postgresql://user:pass@192.168.2.3:5433/kevsrobots_cms
SECRET_KEY=production-secret-key-here
ENVIRONMENT=production
ALLOWED_ORIGINS=https://www.kevsrobots.com,https://kevsrobots.com
```

---

## Troubleshooting

### Common Configuration Issues

**Issue:** Database connection fails

**Check:**
```bash
# Test database connection
psql "$DATABASE_URL" -c "SELECT 1;"
```

**Common Causes:**
- Wrong credentials
- Database server down
- Firewall blocking connection
- Wrong port

---

**Issue:** CORS errors in browser

**Check:**
```bash
# Verify ALLOWED_ORIGINS includes your domain
echo $ALLOWED_ORIGINS
```

**Fix:**
```bash
ALLOWED_ORIGINS=https://www.kevsrobots.com,https://your-domain.com
```

---

**Issue:** Cookies not working

**Causes:**
- HTTP vs HTTPS mismatch
- Domain mismatch
- ENVIRONMENT not set correctly

**Fix:**
```bash
# For production
ENVIRONMENT=production

# For development
ENVIRONMENT=development
```

---

**Issue:** JWT token invalid

**Causes:**
- SECRET_KEY changed
- Token expired
- Clock skew

**Fix:**
- Users must login again
- Ensure system clocks are synchronized
- Generate new SECRET_KEY if compromised

---

## Configuration Checklist

### Before Deploying to Production

- [ ] Generate secure `SECRET_KEY` (min 64 chars)
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure `DATABASE_URL` with production credentials
- [ ] Set `ALLOWED_ORIGINS` to production domains only
- [ ] Verify `.env` file is in `.gitignore`
- [ ] Test database connection
- [ ] Test HTTPS configuration
- [ ] Verify cookies work cross-domain
- [ ] Enable rate limiting
- [ ] Set up database backups
- [ ] Configure monitoring/alerts
- [ ] Document admin credentials securely
- [ ] Review security settings

---

## Related Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide
- [DOCKER.md](DOCKER.md) - Docker setup
- [DATABASE.md](DATABASE.md) - Database configuration
- [AUTHENTICATION.md](AUTHENTICATION.md) - Auth configuration
