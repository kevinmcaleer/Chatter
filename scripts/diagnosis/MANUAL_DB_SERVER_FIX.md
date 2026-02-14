# Manual Database Server Configuration Fix

## Context
Database server (192.168.2.3) was rebuilt after disk failure. Data restored from backup but PostgreSQL configuration needs to be set up again.

## Issue
Chatter servers (192.168.2.2, etc.) cannot connect because pg_hba.conf has default settings.

## Database Credentials
- **Username:** `Hd4AZn:NlSpH` (contains a colon - needs quotes in pg_hba.conf!)
- **Password:** `8&0+6849Mx#S`
- **Database:** `kevsrobots_cms`
- **Port:** `5433`

---

## Manual Fix Steps

### 1. SSH to Database Server
```bash
# First, update SSH known_hosts (server was rebuilt)
ssh-keygen -R 192.168.2.3

# Connect to database server
ssh kev@192.168.2.3
```

### 2. Check if PostgreSQL is Running

**For Docker installation:**
```bash
docker ps | grep postgres
docker logs $(docker ps --filter name=postgres -q)
```

**For native installation:**
```bash
sudo systemctl status postgresql
```

### 3. Verify User Exists

**For Docker:**
```bash
CONTAINER=$(docker ps --filter name=postgres -q | head -1)
docker exec $CONTAINER psql -U postgres -c "\du \"Hd4AZn:NlSpH\""
```

**For native:**
```bash
sudo -u postgres psql -c "\du \"Hd4AZn:NlSpH\""
```

**If user doesn't exist, create it:**
```bash
# For Docker:
docker exec $CONTAINER psql -U postgres << 'EOF'
CREATE USER "Hd4AZn:NlSpH" WITH PASSWORD '8&0+6849Mx#S';
GRANT ALL PRIVILEGES ON DATABASE kevsrobots_cms TO "Hd4AZn:NlSpH";
EOF

# For native:
sudo -u postgres psql << 'EOF'
CREATE USER "Hd4AZn:NlSpH" WITH PASSWORD '8&0+6849Mx#S';
GRANT ALL PRIVILEGES ON DATABASE kevsrobots_cms TO "Hd4AZn:NlSpH";
EOF
```

### 4. Grant Database Permissions

```bash
# For Docker:
docker exec $CONTAINER psql -U postgres kevsrobots_cms << 'EOF'
GRANT ALL PRIVILEGES ON DATABASE kevsrobots_cms TO "Hd4AZn:NlSpH";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "Hd4AZn:NlSpH";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "Hd4AZn:NlSpH";
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO "Hd4AZn:NlSpH";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO "Hd4AZn:NlSpH";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO "Hd4AZn:NlSpH";
EOF

# For native:
sudo -u postgres psql kevsrobots_cms << 'EOF'
GRANT ALL PRIVILEGES ON DATABASE kevsrobots_cms TO "Hd4AZn:NlSpH";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "Hd4AZn:NlSpH";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "Hd4AZn:NlSpH";
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO "Hd4AZn:NlSpH";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO "Hd4AZn:NlSpH";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO "Hd4AZn:NlSpH";
EOF
```

### 5. Find PostgreSQL Configuration Files

**For Docker:**
```bash
CONTAINER=$(docker ps --filter name=postgres -q | head -1)
docker exec $CONTAINER psql -U postgres -c "SHOW config_file;"
docker exec $CONTAINER psql -U postgres -c "SHOW hba_file;"

# Usually:
# config_file: /var/lib/postgresql/data/postgresql.conf
# hba_file: /var/lib/postgresql/data/pg_hba.conf
```

**For native:**
```bash
sudo -u postgres psql -c "SHOW config_file;"
sudo -u postgres psql -c "SHOW hba_file;"

# Usually:
# config_file: /etc/postgresql/16/main/postgresql.conf
# hba_file: /etc/postgresql/16/main/pg_hba.conf
```

### 6. Backup Current Configuration

```bash
sudo mkdir -p /var/backups/postgresql
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# For Docker:
CONTAINER=$(docker ps --filter name=postgres -q | head -1)
docker cp $CONTAINER:/var/lib/postgresql/data/pg_hba.conf /var/backups/postgresql/pg_hba.conf.backup.$TIMESTAMP
docker cp $CONTAINER:/var/lib/postgresql/data/postgresql.conf /var/backups/postgresql/postgresql.conf.backup.$TIMESTAMP

# For native (adjust path based on your version):
sudo cp /etc/postgresql/16/main/pg_hba.conf /var/backups/postgresql/pg_hba.conf.backup.$TIMESTAMP
sudo cp /etc/postgresql/16/main/postgresql.conf /var/backups/postgresql/postgresql.conf.backup.$TIMESTAMP
```

### 7. Edit pg_hba.conf

**IMPORTANT:** The username contains a colon, so it MUST be quoted in pg_hba.conf!

**For Docker:**
```bash
CONTAINER=$(docker ps --filter name=postgres -q | head -1)

# Create new pg_hba.conf
cat > /tmp/pg_hba.conf << 'EOF'
# PostgreSQL Client Authentication Configuration File
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# Local connections
local   all             postgres                                peer
local   all             all                                     peer

# IPv4 local connections:
host    all             postgres        127.0.0.1/32            scram-sha-256

# CHATTER APPLICATION - Username has special characters, must be quoted!
host    kevsrobots_cms  "Hd4AZn:NlSpH"  192.168.2.1/32          md5
host    kevsrobots_cms  "Hd4AZn:NlSpH"  192.168.2.2/32          md5
host    kevsrobots_cms  "Hd4AZn:NlSpH"  192.168.2.3/32          md5
host    kevsrobots_cms  "Hd4AZn:NlSpH"  192.168.2.4/32          md5

# IPv4 local connections
host    all             all             127.0.0.1/32            scram-sha-256

# IPv6 local connections:
host    all             all             ::1/128                 scram-sha-256
EOF

# Copy to container
docker cp /tmp/pg_hba.conf $CONTAINER:/var/lib/postgresql/data/pg_hba.conf
docker exec $CONTAINER chown postgres:postgres /var/lib/postgresql/data/pg_hba.conf
docker exec $CONTAINER chmod 640 /var/lib/postgresql/data/pg_hba.conf
```

**For native (adjust path for your version):**
```bash
sudo tee /etc/postgresql/16/main/pg_hba.conf > /dev/null << 'EOF'
# PostgreSQL Client Authentication Configuration File
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# Local connections
local   all             postgres                                peer
local   all             all                                     peer

# IPv4 local connections:
host    all             postgres        127.0.0.1/32            scram-sha-256

# CHATTER APPLICATION - Username has special characters, must be quoted!
host    kevsrobots_cms  "Hd4AZn:NlSpH"  192.168.2.1/32          md5
host    kevsrobots_cms  "Hd4AZn:NlSpH"  192.168.2.2/32          md5
host    kevsrobots_cms  "Hd4AZn:NlSpH"  192.168.2.3/32          md5
host    kevsrobots_cms  "Hd4AZn:NlSpH"  192.168.2.4/32          md5

# IPv4 local connections
host    all             all             127.0.0.1/32            scram-sha-256

# IPv6 local connections:
host    all             all             ::1/128                 scram-sha-256
EOF

sudo chown postgres:postgres /etc/postgresql/16/main/pg_hba.conf
sudo chmod 640 /etc/postgresql/16/main/pg_hba.conf
```

### 8. Edit postgresql.conf

Ensure PostgreSQL listens on all network interfaces:

**For Docker:**
```bash
CONTAINER=$(docker ps --filter name=postgres -q | head -1)

# Check current setting
docker exec $CONTAINER grep "^listen_addresses" /var/lib/postgresql/data/postgresql.conf

# If not set to '*', add/update it:
docker exec $CONTAINER sh -c "echo \"listen_addresses = '*'\" >> /var/lib/postgresql/data/postgresql.conf"
```

**For native:**
```bash
# Check current setting
sudo grep "^listen_addresses" /etc/postgresql/16/main/postgresql.conf

# If not set to '*', edit the file:
sudo nano /etc/postgresql/16/main/postgresql.conf

# Find and set:
listen_addresses = '*'
port = 5433
```

### 9. Reload/Restart PostgreSQL

**For Docker:**
```bash
CONTAINER=$(docker ps --filter name=postgres -q | head -1)
docker restart $CONTAINER

# Wait for it to start
sleep 5
docker logs $CONTAINER
```

**For native:**
```bash
sudo systemctl reload postgresql
# or for full restart:
# sudo systemctl restart postgresql

sudo systemctl status postgresql
```

### 10. Test Connection

**From database server itself:**
```bash
PGPASSWORD='8&0+6849Mx#S' psql -h 192.168.2.3 -p 5433 -U 'Hd4AZn:NlSpH' -d kevsrobots_cms -c "SELECT version();"
```

**Expected output:**
```
                                                    version
----------------------------------------------------------------------------------------------------------------
 PostgreSQL 16.11 on aarch64-unknown-linux-musl, compiled by gcc (Alpine 15.2.0) 15.2.0, 64-bit
(1 row)
```

### 11. Test from Chatter Server

```bash
# SSH from database server to Chatter server
ssh kev@192.168.2.2

# Test connection
PGPASSWORD='8&0+6849Mx#S' psql -h 192.168.2.3 -p 5433 -U 'Hd4AZn:NlSpH' -d kevsrobots_cms -c "SELECT version();"
```

### 12. Restart Chatter Applications

Once database connection works:

```bash
# On each Chatter server (192.168.2.2, etc.)
cd /path/to/chatter  # Adjust to your deployment path

# If using Docker:
docker-compose restart

# If using systemd:
sudo systemctl restart chatter
```

---

## Troubleshooting

### Connection Still Fails

1. **Check PostgreSQL logs:**
   ```bash
   # Docker:
   docker logs -f $(docker ps --filter name=postgres -q)

   # Native:
   sudo tail -f /var/log/postgresql/postgresql-16-main.log
   ```

2. **Verify pg_hba.conf was loaded:**
   ```bash
   # Docker:
   docker exec $CONTAINER psql -U postgres -c "SELECT pg_reload_conf();"

   # Native:
   sudo -u postgres psql -c "SELECT pg_reload_conf();"
   ```

3. **Check if PostgreSQL is listening on correct port:**
   ```bash
   sudo netstat -tlnp | grep 5433
   # or
   sudo ss -tlnp | grep 5433
   ```

   Should show:
   ```
   tcp  0  0  0.0.0.0:5433  0.0.0.0:*  LISTEN  <pid>/postgres
   ```

4. **Verify username with quotes:**
   The username `Hd4AZn:NlSpH` contains a colon which is normally a separator in PostgreSQL. Make sure:
   - It's quoted in pg_hba.conf: `"Hd4AZn:NlSpH"`
   - It's quoted in psql commands: `'Hd4AZn:NlSpH'` or `"Hd4AZn:NlSpH"`

5. **Check firewall:**
   ```bash
   sudo ufw status
   # If active, allow port:
   sudo ufw allow from 192.168.2.0/24 to any port 5433
   ```

---

## Quick Reference

**Database Connection String:**
```
postgresql://Hd4AZn%3ANlSpH:8%260%2B6849Mx%23S@192.168.2.3:5433/kevsrobots_cms
```

**Test Command:**
```bash
PGPASSWORD='8&0+6849Mx#S' psql -h 192.168.2.3 -p 5433 -U 'Hd4AZn:NlSpH' -d kevsrobots_cms -c "SELECT current_user, current_database();"
```

**Restore Backup if Needed:**
```bash
# Docker:
docker cp /var/backups/postgresql/pg_hba.conf.backup.$TIMESTAMP $CONTAINER:/var/lib/postgresql/data/pg_hba.conf
docker restart $CONTAINER

# Native:
sudo cp /var/backups/postgresql/pg_hba.conf.backup.$TIMESTAMP /etc/postgresql/16/main/pg_hba.conf
sudo systemctl reload postgresql
```
