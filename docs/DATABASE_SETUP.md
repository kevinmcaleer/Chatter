# Database Configuration

The Chatter app supports both **PostgreSQL** (production) and **SQLite** (development/testing).

## Default Configuration

According to `claude.md`, the app should use:
- **PostgreSQL Server:** `192.168.2.1:5433`
- **Database:** `kevsrobots_cms`

## Configuration File

Edit `app/.env` to set your database:

```bash
SECRET_KEY = "593cfcf727eb333e24c83a661f8790dd551aa72bf02a72d355810d36ad8fa8db"

# Database Configuration
DATABASE_URL = "postgresql://username:password@192.168.2.1:5433/kevsrobots_cms"
```

## PostgreSQL Setup

### 1. Install psycopg2

Already included in `requirements.txt`:

```bash
pip install psycopg2-binary
```

### 2. Configure Connection

Update `app/.env` with your PostgreSQL credentials:

```bash
DATABASE_URL = "postgresql://YOUR_USERNAME:YOUR_PASSWORD@192.168.2.1:5433/kevsrobots_cms"
```

### 3. Run Migration

Apply the database schema using the migration SQL file:

```bash
psql -h 192.168.2.1 -p 5433 -U YOUR_USERNAME -d kevsrobots_cms \
  -f migrations/versions/001_add_account_management_with_logging.sql
```

Or let SQLModel create the tables automatically on first run (less recommended for production).

### 4. Verify Connection

```bash
# Test connection
psql -h 192.168.2.1 -p 5433 -U YOUR_USERNAME -d kevsrobots_cms -c "\dt"
```

## SQLite Setup (Development/Testing)

### Option 1: Comment Out DATABASE_URL

In `app/.env`, comment out or remove the DATABASE_URL line:

```bash
SECRET_KEY = "..."

# DATABASE_URL = "postgresql://..."
```

The app will automatically use SQLite: `data/database.db`

### Option 2: Explicitly Set SQLite

```bash
DATABASE_URL = "sqlite:///data/database.db"
```

### SQLite Location

The SQLite database is created at: `data/database.db`

To reset:
```bash
rm data/database.db
# Restart server - it will recreate
```

## Current Status

**Right now**, the server is configured for:
- ✅ PostgreSQL at `192.168.2.1:5433/kevsrobots_cms`
- But currently running with **SQLite** fallback (no credentials provided)

## How to Switch

### To PostgreSQL:

1. Get PostgreSQL credentials for `192.168.2.1:5433`
2. Update `app/.env`:
   ```bash
   DATABASE_URL = "postgresql://realuser:realpass@192.168.2.1:5433/kevsrobots_cms"
   ```
3. Install psycopg2: `pip install psycopg2-binary`
4. Restart server
5. Apply migration SQL if needed

### To SQLite:

1. Edit `app/.env` and comment out DATABASE_URL:
   ```bash
   # DATABASE_URL = "postgresql://..."
   ```
2. Restart server
3. Database auto-creates at `data/database.db`

## Database Schema

The app expects these tables:
- `user` - User accounts
- `accountlog` - Audit log of account changes
- `like` - User likes
- `comment` - User comments

### Migration Files

- **Forward:** `migrations/versions/001_add_account_management_with_logging.sql`
- **Rollback:** `migrations/versions/001_add_account_management_with_logging_rollback.sql`

## Troubleshooting

### "Connection refused" or "could not connect"

- Check if PostgreSQL server is running
- Verify IP address and port
- Check firewall rules
- Verify database exists

### "no such column" errors

- Database schema is outdated
- **For SQLite:** Delete `data/database.db` and restart
- **For PostgreSQL:** Run migration SQL

### "authentication failed"

- Check username and password
- Verify user has access to the database
- Check PostgreSQL `pg_hba.conf` for allowed connections

## Environment Variables Reference

```bash
# Required
SECRET_KEY = "your-secret-key"

# Database (choose one)
DATABASE_URL = "postgresql://user:pass@192.168.2.1:5433/kevsrobots_cms"  # PostgreSQL
# DATABASE_URL = "sqlite:///data/database.db"  # SQLite
# Or leave commented for automatic SQLite fallback
```

## Testing Different Databases

You can run tests against different databases:

```bash
# Test with SQLite (default)
pytest tests/test_accounts.py

# Test with PostgreSQL
DATABASE_URL="postgresql://user:pass@192.168.2.1:5433/kevsrobots_cms_test" \
  pytest tests/test_accounts.py
```

## Production Recommendations

1. ✅ Use PostgreSQL for production
2. ✅ Store DATABASE_URL in environment variables (not in `.env` file)
3. ✅ Use connection pooling for better performance
4. ✅ Run migrations manually (not auto-create tables)
5. ✅ Set up database backups
6. ✅ Use read replicas for scaling
7. ✅ Monitor connection pool usage

## Next Steps

**To use PostgreSQL now:**
1. Get credentials for `192.168.2.1:5433/kevsrobots_cms`
2. Update `app/.env` with real credentials
3. Run: `pip install psycopg2-binary`
4. Restart the server
5. Apply migration if database is empty

**To continue with SQLite:**
1. Comment out DATABASE_URL in `app/.env`
2. Restart server
3. Continue testing!
