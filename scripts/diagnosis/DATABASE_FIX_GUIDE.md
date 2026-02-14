# Database Connection Fix Guide for 192.168.2.3

## Problem
Chatter servers (192.168.2.2, etc.) cannot connect to PostgreSQL on 192.168.2.3:5433
Error: `password authentication failed for user "kev"`

## Diagnosis Results
- ✓ Network connectivity is working (server responds on port 5433)
- ✗ Authentication is failing (password or pg_hba.conf issue)

## Step-by-Step Fix

### 1. SSH into the database server
```bash
ssh kev@192.168.2.3
```

### 2. Find your PostgreSQL version and config files
```bash
# Check PostgreSQL version
psql --version

# Find config file locations
sudo -u postgres psql -c "SHOW config_file;"
sudo -u postgres psql -c "SHOW hba_file;"
```

### 3. Check if user 'kev' exists in PostgreSQL
```bash
sudo -u postgres psql -c "\du kev"
```

**If user doesn't exist, create it:**
```bash
sudo -u postgres psql << EOF
CREATE USER kev WITH PASSWORD 'monkeybaby';
GRANT ALL PRIVILEGES ON DATABASE kevsrobots_cms TO kev;
EOF
```

### 4. Check pg_hba.conf configuration
```bash
# View current pg_hba.conf (adjust path based on your PostgreSQL version)
sudo cat /etc/postgresql/15/main/pg_hba.conf | grep -v '^#' | grep -v '^$'
```

### 5. Fix pg_hba.conf to allow connections from Chatter servers

**Edit the file:**
```bash
# For PostgreSQL 15 (adjust version number as needed)
sudo nano /etc/postgresql/15/main/pg_hba.conf
```

**Add these lines BEFORE the existing rules:**
```
# TYPE  DATABASE        USER    ADDRESS         METHOD
# Allow Chatter servers to connect
host    kevsrobots_cms  kev     192.168.2.1/32  md5
host    kevsrobots_cms  kev     192.168.2.2/32  md5
host    kevsrobots_cms  kev     192.168.2.3/32  md5
host    kevsrobots_cms  kev     192.168.2.4/32  md5

# Or use subnet (simpler but less secure)
# host    kevsrobots_cms  kev     192.168.2.0/24  md5
```

**Important:** Make sure these lines come BEFORE any more general rules (like `host all all ...`)

### 6. Verify postgresql.conf is listening on all interfaces
```bash
# Check current setting
sudo grep "^listen_addresses" /etc/postgresql/15/main/postgresql.conf

# Should be:
# listen_addresses = '*'

# If not, edit it:
sudo nano /etc/postgresql/15/main/postgresql.conf

# Find and set:
listen_addresses = '*'
port = 5433
```

### 7. Reload PostgreSQL configuration
```bash
# Reload (doesn't disconnect existing connections)
sudo systemctl reload postgresql

# Or restart (more thorough, disconnects users)
# sudo systemctl restart postgresql
```

### 8. Test the connection from the database server itself
```bash
# Test local connection
psql -h localhost -p 5433 -U kev -d kevsrobots_cms -c "SELECT version();"

# Test from network interface
psql -h 192.168.2.3 -p 5433 -U kev -d kevsrobots_cms -c "SELECT version();"
```

### 9. Test from a Chatter server (192.168.2.2)
```bash
ssh kev@192.168.2.2
psql -h 192.168.2.3 -p 5433 -U kev -d kevsrobots_cms -c "SELECT version();"
```

## Common Issues and Solutions

### Issue: User 'kev' doesn't have password set
```bash
sudo -u postgres psql << EOF
ALTER USER kev WITH PASSWORD 'monkeybaby';
EOF
```

### Issue: User 'kev' doesn't have database permissions
```bash
sudo -u postgres psql << EOF
GRANT ALL PRIVILEGES ON DATABASE kevsrobots_cms TO kev;
\c kevsrobots_cms
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO kev;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO kev;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO kev;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO kev;
EOF
```

### Issue: Firewall blocking port 5433
```bash
# Check if firewall is active
sudo ufw status

# If active, allow PostgreSQL port
sudo ufw allow from 192.168.2.0/24 to any port 5433
```

### Issue: PostgreSQL not listening on port 5433
```bash
# Check what ports PostgreSQL is listening on
sudo netstat -tlnp | grep postgres
# or
sudo ss -tlnp | grep postgres

# Should show something like:
# tcp  0  0  0.0.0.0:5433  0.0.0.0:*  LISTEN  <pid>/postgres
```

## Verification Commands

After making changes, verify everything works:

```bash
# 1. Check PostgreSQL is running
sudo systemctl status postgresql

# 2. Check it's listening on correct port
sudo ss -tlnp | grep 5433

# 3. Check pg_hba.conf was reloaded
sudo -u postgres psql -c "SELECT pg_reload_conf();"

# 4. Check current connections
sudo -u postgres psql -c "SELECT datname, usename, client_addr, state FROM pg_stat_activity WHERE datname='kevsrobots_cms';"

# 5. Test connection from Chatter server
# (Run this from 192.168.2.2)
psql -h 192.168.2.3 -p 5433 -U kev -d kevsrobots_cms -c "SELECT current_database(), current_user;"
```

## Example Working pg_hba.conf

```
# PostgreSQL Client Authentication Configuration File
# ===================================================

# TYPE  DATABASE        USER            ADDRESS                 METHOD

# "local" is for Unix domain socket connections only
local   all             postgres                                peer
local   all             all                                     peer

# IPv4 local connections:
host    all             postgres        127.0.0.1/32            scram-sha-256

# Allow Chatter servers to connect to kevsrobots_cms
host    kevsrobots_cms  kev             192.168.2.1/32          md5
host    kevsrobots_cms  kev             192.168.2.2/32          md5
host    kevsrobots_cms  kev             192.168.2.3/32          md5
host    kevsrobots_cms  kev             192.168.2.4/32          md5

# IPv4 local connections:
host    all             all             127.0.0.1/32            scram-sha-256

# IPv6 local connections:
host    all             all             ::1/128                 scram-sha-256
```

## Notes

- The order of rules in pg_hba.conf matters - first match wins
- `md5` authentication method is used for password authentication
- `peer` authentication is for local Unix socket connections
- After changing pg_hba.conf, always reload: `sudo systemctl reload postgresql`
- Check PostgreSQL logs for detailed errors: `sudo tail -f /var/log/postgresql/postgresql-15-main.log`
