# How to Fix Your .env File for Production

## Common .env Configuration Errors

This guide explains how to fix common mistakes in `.env` files for Docker deployment.

### ❌ Problem 1: DB_HOST includes port number
```bash
# WRONG:
DB_HOST=192.168.2.3:5433

# CORRECT:
DB_HOST=192.168.2.3
```
The port should NOT be in DB_HOST. It goes in DB_PORT instead.

---

### ❌ Problem 2: Wrong port number
```bash
# Make sure DB_PORT matches your actual PostgreSQL port
DB_PORT=5433  # or whatever port your PostgreSQL is running on
```

---

### ❌ Problem 3: Special characters not URL-encoded

If your username or password contains special characters, they MUST be URL-encoded.

**Example Username with colon: `user:name`**
- Contains `:` (colon) which is a URL delimiter
- Must be encoded as `user%3Aname`

**Example Password with special chars: `pass&word+123#`**
- Contains `&`, `+`, and `#` which are special URL characters
- Must be encoded as `pass%26word%2B123%23`

**URL Encoding Reference:**
- `:` → `%3A`
- `@` → `%40`
- `#` → `%23`
- `&` → `%26`
- `+` → `%2B`
- `/` → `%2F`
- `?` → `%3F`
- `=` → `%3D`
- ` ` (space) → `%20`

```bash
# Example - WRONG:
DB_USER=admin:user
DB_PASSWORD=my&secure+pass#123

# Example - CORRECT (URL-encoded):
DB_USER=admin%3Auser
DB_PASSWORD=my%26secure%2Bpass%23123
```

---

### ❌ Problem 4: SECRET_KEY not changed
```bash
# WRONG (placeholder):
SECRET_KEY=your_secret_key_here_replace_me

# CORRECT (generate a unique one):
SECRET_KEY=<your_generated_secret_key>
```

Generate a new one with:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## Complete .env File Template

Copy this template and fill in YOUR actual values:

```bash
# ============================================
# Application Settings
# ============================================

ENVIRONMENT=production
PORT=8006

# Generate with: python3 -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=<your_generated_secret_key_here>

ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# ============================================
# Database Settings
# ============================================

# Database host (IP or hostname ONLY - no port!)
DB_HOST=your.database.host

# Database port
DB_PORT=5432

# Database name
DB_NAME=your_database_name

# Database username (URL-encode if it contains special characters)
DB_USER=your_username

# Database password (URL-encode if it contains special characters)
DB_PASSWORD=your_password
```

**IMPORTANT:**
- Replace ALL placeholder values with your actual credentials
- URL-encode any special characters in username/password (see reference above)
- Generate a unique SECRET_KEY
- NEVER commit this file to git

---

## How docker-compose Uses These Variables

The `docker-compose.yml` constructs the DATABASE_URL like this:

```yaml
DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}
```

Example result (with URL-encoded credentials):
```
postgresql://admin%3Auser:pass%26word@db.example.com:5432/mydb
```

This is why proper encoding is critical!

---

## Steps to Fix on Production Machine

1. **Backup your current .env:**
   ```bash
   cp .env .env.backup
   ```

2. **Edit the .env file:**
   ```bash
   nano .env
   ```

3. **Fix these issues:**
   - Remove port from `DB_HOST` (should be just hostname/IP)
   - Set correct `DB_PORT`
   - URL-encode special characters in `DB_USER` (`:` becomes `%3A`, etc.)
   - URL-encode special characters in `DB_PASSWORD` (`&` → `%26`, `+` → `%2B`, `#` → `%23`)
   - Generate and set a real `SECRET_KEY`

4. **Save and test:**
   ```bash
   # Test database connection (will use your .env values)
   docker run --rm --env-file .env postgres:16-alpine \
     psql "postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}" \
     -c "SELECT version();"
   ```

5. **Start your container:**
   ```bash
   docker-compose up -d
   # or
   docker run -p 8006:8006 --env-file .env chatter:latest
   ```

---

## Verification

After fixing, the container should connect successfully:

```
========================================
Chatter Docker Container Starting
========================================

Checking database connection...
Waiting for database to be ready...
✅ Database is ready!

Checking and applying migrations...
========================================
✓ Migration schema_version already applied
✓ Migration 000 already applied
========================================
✅ All migrations checked/applied
========================================

Starting application...
```

---

## Still Having Issues?

If it still doesn't work after these fixes:

1. **Check network connectivity:**
   ```bash
   nc -zv <your_db_host> <your_db_port>
   ```

2. **Check PostgreSQL logs on your database server:**
   ```bash
   sudo tail -100 /var/log/postgresql/postgresql-*.log
   ```

3. **Verify pg_hba.conf allows connections from your production machine IP**

4. **Run with debug entrypoint to see exact error:**
   ```bash
   docker run -p 8006:8006 --env-file .env \
     --entrypoint /app/docker-entrypoint-debug.sh \
     chatter:latest
   ```

5. **Use the troubleshooting script:**
   ```bash
   ./troubleshoot-db.sh
   ```

---

## Security Reminder

- **NEVER commit `.env` files to git**
- **NEVER share credentials in documentation or commits**
- **Use `.gitignore` to block `.env*` files**
- **Rotate credentials if they're accidentally exposed**
- **Use environment-specific files** (`.env.production`, `.env.development`) that are NOT committed
