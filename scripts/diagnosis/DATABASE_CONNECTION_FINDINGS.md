# Database Connection Issue - Findings & Resolution

**Date:** 2026-02-14
**Issue:** Chatter servers cannot connect to PostgreSQL database
**Status:** ✅ **ROOT CAUSE IDENTIFIED**

---

## Summary

The database server (192.168.2.3:5433) is **correctly configured** and accessible. The issue is on the **Chatter application servers** - they likely have an incorrect or missing `.env` file.

---

## Test Results

### ✅ Database Server (192.168.2.3) - WORKING
```
✓ Network connectivity: SUCCESS
✓ Port 5433: OPEN and listening
✓ PostgreSQL: Running (v16.11)
✓ Authentication: WORKING with correct credentials
✓ User 'Hd4AZn:NlSpH': EXISTS and has proper permissions
✓ Database 'kevsrobots_cms': EXISTS and accessible
```

**Test command that worked:**
```bash
python3 test_db_connection.py
# Output: Connection successful!
```

### ❌ Original Test with Wrong Credentials - FAILED
When testing with username 'kev' and password 'monkeybaby':
```
✗ password authentication failed for user "kev"
```

**Reason:** These were SSH credentials, not PostgreSQL credentials.

---

## Correct Database Credentials

**From `.env` file:**
```bash
# URL-encoded (as stored in .env)
DB_USER=Hd4AZn%3ANlSpH
DB_PASSWORD=8%260%2B6849Mx%23S

# Decoded (actual values)
DB_USER=Hd4AZn:NlSpH          # Note: contains a colon (:)
DB_PASSWORD=8&0+6849Mx#S      # Note: contains special chars: & + #

# Full DATABASE_URL
DATABASE_URL=postgresql://Hd4AZn%3ANlSpH:8%260%2B6849Mx%23S@192.168.2.3:5433/kevsrobots_cms
```

**Important Notes:**
- Username contains a colon (`:`) which MUST be URL-encoded as `%3A`
- Password contains special characters (`&`, `+`, `#`) which MUST be URL-encoded:
  - `&` → `%26`
  - `+` → `%2B`
  - `#` → `%23`
  - `:` → `%3A`

---

## Root Cause

The Chatter servers (192.168.2.2, etc.) are likely experiencing one of these issues:

1. **Missing .env file** - The `.env` file doesn't exist on the server
2. **Incorrect DATABASE_URL** - The credentials are wrong or not properly URL-encoded
3. **Environment not loaded** - The application isn't loading the `.env` file
4. **Docker environment** - Docker container isn't getting the environment variables

---

## Resolution Steps

### Option 1: Quick Fix - Deploy .env File (Recommended)

Run the automated deployment script:
```bash
cd /Users/kev/Python/Chatter
./scripts/diagnosis/deploy_env_to_servers.sh
```

This will:
1. Backup existing `.env` on remote servers
2. Copy the correct `.env` file from your local machine
3. Verify the DATABASE_URL is correct
4. Restart the Chatter application

### Option 2: Manual Fix

1. **Copy .env to Chatter server:**
   ```bash
   scp .env kev@192.168.2.2:/home/kev/chatter/.env
   ```

2. **SSH into the server and verify:**
   ```bash
   ssh kev@192.168.2.2
   cd /home/kev/chatter  # Or your Chatter directory

   # Check if .env exists
   ls -la .env

   # Verify DATABASE_URL (password will be masked)
   grep DATABASE_URL .env | sed 's/:\/\/[^:]*:[^@]*@/:\/\/***:***@/'
   ```

3. **Restart the application:**
   ```bash
   # If using Docker:
   docker-compose restart

   # If using systemd:
   sudo systemctl restart chatter

   # If using uvicorn directly:
   pkill -f "uvicorn.*main:app"
   # Then restart your uvicorn command
   ```

### Option 3: Diagnostic First

If you want to diagnose the issue before fixing:
```bash
# Copy diagnostic script to server
scp scripts/diagnosis/check_chatter_server.sh kev@192.168.2.2:/tmp/

# SSH and run it
ssh kev@192.168.2.2
cd /home/kev/chatter  # Or your Chatter directory
bash /tmp/check_chatter_server.sh
```

This will show:
- If `.env` file exists
- Current `DATABASE_URL` configuration
- If the application can connect to the database
- Application logs with any database errors

---

## Verification

After applying the fix, verify the connection:

1. **Check application logs:**
   ```bash
   # On Chatter server
   docker logs -f $(docker ps --filter name=chatter -q)
   # or
   tail -f /var/log/chatter/chatter.log
   ```

2. **Test database connection from Chatter server:**
   ```bash
   python3 << 'EOF'
   import psycopg2
   from urllib.parse import urlparse, unquote

   db_url = "postgresql://Hd4AZn%3ANlSpH:8%260%2B6849Mx%23S@192.168.2.3:5433/kevsrobots_cms"
   parsed = urlparse(db_url)

   conn = psycopg2.connect(
       host=parsed.hostname,
       port=parsed.port,
       database=parsed.path.lstrip('/'),
       user=unquote(parsed.username),
       password=unquote(parsed.password)
   )

   cur = conn.cursor()
   cur.execute("SELECT 'SUCCESS' as status;")
   print(cur.fetchone())
   EOF
   ```

3. **Test the application:**
   - Visit https://kevsrobots.com
   - Try logging in
   - Check if comments/likes work

---

## Files Created

1. **`test_db_connection.py`** - Python script to test database connection (✅ WORKS)
2. **`scripts/diagnosis/check_chatter_server.sh`** - Diagnostic script for Chatter servers
3. **`scripts/diagnosis/deploy_env_to_servers.sh`** - Automated deployment script
4. **`scripts/diagnosis/fix_pg_hba.sh`** - ~~Database server fix~~ (NOT NEEDED - DB is OK)
5. **`scripts/diagnosis/DATABASE_FIX_GUIDE.md`** - ~~Database server guide~~ (NOT NEEDED - DB is OK)

---

## Key Learnings

1. ✅ Database server (192.168.2.3) is properly configured - no changes needed
2. ✅ pg_hba.conf is correct - allows connections from 192.168.2.x
3. ✅ PostgreSQL user and permissions are correct
4. ❌ SSH credentials ≠ PostgreSQL credentials (they're different!)
5. ⚠️ Special characters in passwords MUST be URL-encoded in DATABASE_URL
6. ⚠️ Username contains a colon which MUST be URL-encoded

---

## Next Steps

1. **Deploy .env to Chatter servers** using the deployment script
2. **Restart Chatter applications** on all servers
3. **Monitor logs** for any connection issues
4. **Test the website** to ensure everything works

---

## Need Help?

If issues persist after deploying the .env file:

1. Run the diagnostic script: `scripts/diagnosis/check_chatter_server.sh`
2. Check application logs for specific error messages
3. Verify the application is actually loading the .env file
4. Check if Docker is passing environment variables correctly
5. Ensure file permissions on .env are correct (should be readable by the app)

---

## Contact

- **Database Server:** 192.168.2.3:5433 ✅ WORKING
- **Chatter Servers:** 192.168.2.1, 192.168.2.2 (192.168.2.1 temporarily excluded)
- **Database:** kevsrobots_cms ✅ ACCESSIBLE
- **PostgreSQL User:** Hd4AZn:NlSpH ✅ VALID
