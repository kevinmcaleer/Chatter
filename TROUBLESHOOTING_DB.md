# PostgreSQL Connection Troubleshooting

## Error: Connection Refused to 192.168.2.1:5433

```
connection to server at "192.168.2.1", port 5433 failed: Connection refused
Is the server running on that host and accepting TCP/IP connections?
```

This error means your computer cannot reach the PostgreSQL server. Here's how to fix it:

## Step 1: Check if PostgreSQL Server is Running

SSH into the server (192.168.2.1) and check:

```bash
# SSH to the server
ssh user@192.168.2.1

# Check if PostgreSQL is running
sudo systemctl status postgresql

# Or check if the port is listening
sudo netstat -nltp | grep 5433

# Or
sudo lsof -i :5433
```

If PostgreSQL is not running, start it:

```bash
sudo systemctl start postgresql
# or
sudo service postgresql start
```

## Step 2: Check PostgreSQL Configuration

PostgreSQL might not be configured to accept remote connections.

### Check if PostgreSQL is listening on the right interface:

```bash
# Look for listen_addresses in postgresql.conf
sudo grep "listen_addresses" /etc/postgresql/*/main/postgresql.conf

# It should be:
listen_addresses = '*'
# or
listen_addresses = '192.168.2.1'
```

If it says `listen_addresses = 'localhost'`, you need to change it:

```bash
sudo nano /etc/postgresql/*/main/postgresql.conf

# Change:
# listen_addresses = 'localhost'
# To:
listen_addresses = '*'

# Save and restart PostgreSQL
sudo systemctl restart postgresql
```

### Check if the port is correct:

```bash
sudo grep "port" /etc/postgresql/*/main/postgresql.conf

# Should show:
port = 5433
```

## Step 3: Check Firewall Rules

The server firewall might be blocking port 5433.

```bash
# Check firewall status
sudo ufw status

# If active, allow port 5433
sudo ufw allow 5433/tcp

# Or check iptables
sudo iptables -L -n | grep 5433
```

## Step 4: Check pg_hba.conf (PostgreSQL Access Control)

PostgreSQL uses `pg_hba.conf` to control who can connect.

```bash
# Edit pg_hba.conf
sudo nano /etc/postgresql/*/main/pg_hba.conf

# Add this line to allow connections from your network:
# TYPE  DATABASE        USER            ADDRESS                 METHOD
host    all             all             192.168.2.0/24          md5

# Or to allow from your specific IP (safer):
host    all             all             YOUR_IP_HERE/32         md5

# Save and reload PostgreSQL
sudo systemctl reload postgresql
```

## Step 5: Test Connection from Server

While SSH'd into the server, test local connection:

```bash
# Test local connection
psql -h localhost -p 5433 -U your_db_user -d kevsrobots_cms

# Or
psql -h 192.168.2.1 -p 5433 -U your_db_user -d kevsrobots_cms
```

## Step 6: Test Connection from Your Mac

From your Mac, try pinging the server:

```bash
# Test network connectivity
ping 192.168.2.1

# Test if port is reachable
nc -zv 192.168.2.1 5433

# Or use telnet
telnet 192.168.2.1 5433
```

## Quick Fix Checklist

On the PostgreSQL server (192.168.2.1):

```bash
# 1. Check PostgreSQL is running
sudo systemctl status postgresql

# 2. Check it's listening on port 5433
sudo netstat -nltp | grep 5433

# 3. Check postgresql.conf
sudo grep "listen_addresses\|port" /etc/postgresql/*/main/postgresql.conf

# 4. Check pg_hba.conf allows your connection
sudo cat /etc/postgresql/*/main/pg_hba.conf | grep -v "^#"

# 5. Restart PostgreSQL after any changes
sudo systemctl restart postgresql
```

## Alternative: Use SSH Tunnel

If you can't get direct access working, you can use an SSH tunnel:

```bash
# On your Mac, create SSH tunnel
ssh -L 5433:localhost:5433 user@192.168.2.1

# Then update your DATABASE_URL to use localhost:
DATABASE_URL="postgresql://your_db_user:your_db_password@localhost:5433/kevsrobots_cms"

# Keep the SSH tunnel running and apply migrations
```

## Common Issues

### Issue: "FATAL: password authentication failed"
- Wrong username or password
- Check credentials are correct
- Try connecting with psql directly

### Issue: "FATAL: database does not exist"
- Database hasn't been created
- Create it: `CREATE DATABASE kevsrobots_cms;`

### Issue: "Connection timed out"
- Firewall blocking
- Wrong IP address
- Server not reachable on network

## Need Help?

1. What's the output of `systemctl status postgresql`?
2. What's in `pg_hba.conf`?
3. What's the `listen_addresses` setting?
4. Can you ping 192.168.2.1?
5. Can you SSH to 192.168.2.1?

Once you've checked these, we can proceed with the migrations.
