# Docker Deployment Guide

This guide explains how to deploy the Chatter application using Docker and docker-compose.

## Features

- ✅ **Automatic migrations** - Database migrations run automatically on container startup
- ✅ **Migration versioning** - Tracks which migrations have been applied
- ✅ **Idempotent startup** - Safe to restart containers, migrations won't re-run
- ✅ **Health checks** - Built-in health monitoring
- ✅ **Multi-stage build** - Optimized image size
- ✅ **Non-root user** - Runs as unprivileged user for security
- ✅ **PostgreSQL included** - Optional built-in database or use external

## Quick Start

### 1. Prepare Environment

```bash
# Copy environment template
cp .env.docker .env

# Edit .env and set your values
nano .env
```

**Required settings:**
- `SECRET_KEY` - Generate with: `python3 -c "import secrets; print(secrets.token_hex(32))"`
- `DB_PASSWORD` - Set a secure database password

### 2. Build and Run

**Option A: With Built-in PostgreSQL**
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f app
```

**Option B: With External PostgreSQL**
```bash
# Edit docker-compose.yml and comment out the postgres service
# Update .env with external database settings

# Start only the app
docker-compose up -d app

# View logs
docker-compose logs -f app
```

### 3. Verify Deployment

```bash
# Check container status
docker-compose ps

# Check health
curl http://localhost:8000/health

# Check API docs
open http://localhost:8000/docs
```

### 4. Create Admin User

```bash
# Register first user
curl -X POST http://localhost:8000/accounts/register \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "admin",
    "firstname": "Admin",
    "lastname": "User",
    "email": "admin@kevsrobots.com",
    "password": "SecurePass123"
  }'

# Make them admin
docker-compose exec postgres psql -U chatter_user -d kevsrobots_cms \
  -c "UPDATE \"user\" SET type=1 WHERE username='admin';"
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SECRET_KEY` | JWT secret key | - | ✅ Yes |
| `ENVIRONMENT` | Environment mode | `production` | No |
| `DATABASE_URL` | Full database connection string | Constructed from DB_* vars | No |
| `DB_HOST` | Database hostname | `postgres` | Yes |
| `DB_PORT` | Database port | `5432` | Yes |
| `DB_NAME` | Database name | `kevsrobots_cms` | Yes |
| `DB_USER` | Database username | - | ✅ Yes |
| `DB_PASSWORD` | Database password | - | ✅ Yes |
| `ALLOWED_ORIGINS` | CORS allowed origins | `https://kevsrobots.com` | No |
| `PORT` | Application port | `8000` | No |

### Using External PostgreSQL

If you're using an existing PostgreSQL server (like 192.168.2.3:5433):

1. **Update .env**:
```bash
DB_HOST=192.168.2.3
DB_PORT=5433
DB_NAME=kevsrobots_cms
DB_USER=your_db_user  # URL-encoded if contains special chars
DB_PASSWORD=your_db_password  # URL-encoded if contains special chars
```

2. **Comment out postgres service** in docker-compose.yml:
```yaml
# Comment out or remove the entire postgres section
# postgres:
#   image: postgres:16-alpine
#   ...
```

3. **Update app service dependency**:
```yaml
app:
  # Remove or comment out:
  # depends_on:
  #   postgres:
  #     condition: service_healthy
```

## Migration System

### How It Works

1. **Container starts** → `docker-entrypoint.sh` runs
2. **Waits for database** → Up to 30 attempts, 2 seconds between
3. **Checks schema_version table** → Creates if doesn't exist
4. **Applies missing migrations** → Only runs new migrations
5. **Starts application** → `uvicorn app.main:app`

### Migration Files

Migrations are located in `migrations/versions/`:

- `schema_version.sql` - Creates version tracking table
- `000_create_initial_schema.sql` - Creates all tables

### Adding New Migrations

1. **Create migration file**:
```bash
# Create new migration
nano migrations/versions/003_add_new_feature.sql
```

2. **Add to docker-entrypoint.sh**:
```bash
declare -a migrations=(
    "migrations/versions/schema_version.sql:schema_version:Create schema version tracking table"
    "migrations/versions/000_create_initial_schema.sql:000:Create initial database schema"
    "migrations/versions/003_add_new_feature.sql:003:Add new feature"  # Add this line
)
```

3. **Rebuild and restart**:
```bash
docker-compose build app
docker-compose up -d app
```

The new migration will be applied automatically on startup.

### Checking Applied Migrations

```bash
# Connect to database
docker-compose exec postgres psql -U chatter_user -d kevsrobots_cms

# View applied migrations
SELECT version, description, applied_at FROM schema_version ORDER BY applied_at;
```

## Docker Commands

### Building

```bash
# Build without cache
docker-compose build --no-cache

# Build specific service
docker-compose build app

# Build with build args
docker-compose build --build-arg PYTHON_VERSION=3.13
```

### Running

```bash
# Start in background
docker-compose up -d

# Start with logs
docker-compose up

# Start specific service
docker-compose up -d app

# Start with nginx
docker-compose --profile with-nginx up -d
```

### Logs

```bash
# Follow all logs
docker-compose logs -f

# Follow app logs only
docker-compose logs -f app

# Last 100 lines
docker-compose logs --tail=100 app

# Logs since timestamp
docker-compose logs --since 2025-10-22T10:00:00
```

### Stopping

```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Stop specific service
docker-compose stop app
```

### Maintenance

```bash
# Restart service
docker-compose restart app

# Execute command in container
docker-compose exec app python --version

# Access container shell
docker-compose exec app /bin/bash

# View container stats
docker stats chatter-app
```

## Production Deployment

### 1. Security Checklist

- [ ] Set strong `SECRET_KEY`
- [ ] Set strong `DB_PASSWORD`
- [ ] Use HTTPS (configure nginx or use reverse proxy)
- [ ] Set `ALLOWED_ORIGINS` to your actual domain
- [ ] Enable firewall rules
- [ ] Regular security updates: `docker-compose pull && docker-compose up -d`

### 2. Performance Tuning

**PostgreSQL:**
```yaml
postgres:
  environment:
    - POSTGRES_MAX_CONNECTIONS=100
    - POSTGRES_SHARED_BUFFERS=256MB
```

**Application:**
```yaml
app:
  environment:
    - WORKERS=4  # Add if implementing gunicorn
```

### 3. Monitoring

**Health Checks:**
```bash
# Check if container is healthy
docker inspect --format='{{.State.Health.Status}}' chatter-app

# Health check logs
docker inspect --format='{{range .State.Health.Log}}{{.Output}}{{end}}' chatter-app
```

**Resource Usage:**
```bash
# Container stats
docker stats chatter-app

# Disk usage
docker system df
```

### 4. Backups

**Database Backup:**
```bash
# Backup
docker-compose exec postgres pg_dump -U chatter_user kevsrobots_cms > backup.sql

# Restore
docker-compose exec -T postgres psql -U chatter_user kevsrobots_cms < backup.sql
```

**Full System Backup:**
```bash
# Stop containers
docker-compose down

# Backup volumes
docker run --rm -v chatter_postgres-data:/data -v $(pwd):/backup alpine \
  tar czf /backup/postgres-data-backup.tar.gz -C /data .

# Start containers
docker-compose up -d
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs app

# Check database connection
docker-compose exec app python3 -c "
import psycopg2
import os
print(psycopg2.connect(os.getenv('DATABASE_URL')))
"
```

### Migration Fails

```bash
# View migration logs in container startup
docker-compose logs app | grep -A 10 "migration"

# Manually run migrations
docker-compose exec app python3 apply_migrations.py

# Check schema_version table
docker-compose exec postgres psql -U chatter_user -d kevsrobots_cms \
  -c "SELECT * FROM schema_version;"
```

### Database Connection Issues

```bash
# Check if postgres is healthy
docker-compose ps

# Test connection from app container
docker-compose exec app psql -h postgres -U chatter_user -d kevsrobots_cms

# Check network
docker network inspect chatter_chatter-network
```

### Permission Errors

```bash
# Fix data directory permissions
sudo chown -R 1000:1000 ./data

# Check user in container
docker-compose exec app whoami
docker-compose exec app id
```

## Advanced Configuration

### Using Nginx Reverse Proxy

1. **Create nginx config**:
```bash
mkdir -p nginx
nano nginx/nginx.conf
```

2. **Start with nginx**:
```bash
docker-compose --profile with-nginx up -d
```

### Multi-Container Scaling

```bash
# Run multiple app instances
docker-compose up -d --scale app=3
```

### Custom Build

```bash
# Build with custom tag
docker build -t myregistry.com/chatter:v1.0 .

# Push to registry
docker push myregistry.com/chatter:v1.0
```

## Support

- **Issues**: See `TROUBLESHOOTING_DB.md`
- **Migrations**: See migration files in `migrations/versions/`
- **Security**: See `design/PRE_DEPLOYMENT_SUMMARY.md`
- **Tasks**: See `design/deployment_tasks.md`
