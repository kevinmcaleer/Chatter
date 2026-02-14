# Docker Deployment - Quick Reference

This is a quick reference for deploying Chatter using Docker. For full documentation, see [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md).

## Prerequisites

- Docker 20.10+
- docker-compose 1.29+
- 2GB RAM minimum
- 10GB disk space

## Quick Start (3 steps)

```bash
# 1. Configure environment
cp .env.docker .env
nano .env  # Set SECRET_KEY and DB_PASSWORD

# 2. Build and start
make build
make run

# 3. Create admin user
curl -X POST http://localhost:8000/accounts/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","firstname":"Admin","lastname":"User","email":"admin@kevsrobots.com","password":"SecurePass123"}'
```

## Common Commands

```bash
# Development
make build          # Build image
make run            # Start containers
make logs           # Follow logs
make stop           # Stop containers
make shell          # Access container shell

# Database
make db-shell       # PostgreSQL shell
make backup-db      # Backup database
make restore-db FILE=backup.sql

# Production
make deploy-prod    # Build, tag, and push to registry
```

## Using Makefile

The project includes a Makefile for common operations:

```bash
make help           # Show all available commands
make build          # Build Docker image
make run            # Start with docker-compose
make logs           # View logs
make stop           # Stop all containers
make clean          # Stop and remove volumes
make test           # Run tests
make health         # Check application health
```

## Deployment to Production Server

### Option 1: Using Local Registry (Recommended)

```bash
# On development machine
make deploy-prod

# On production server
docker pull 192.168.2.1:5000/kevsrobots/chatter:latest
docker-compose up -d
```

### Option 2: Export/Import Image

```bash
# Save image
docker save chatter:latest | gzip > chatter-latest.tar.gz

# Copy to server
scp chatter-latest.tar.gz user@192.168.2.3:/tmp/

# Load on server
docker load < /tmp/chatter-latest.tar.gz
docker-compose up -d
```

## Environment Variables

Minimum required variables in `.env`:

```bash
SECRET_KEY=your_generated_secret_key_here
DB_USER=chatter_user
DB_PASSWORD=secure_password_here
DB_NAME=kevsrobots_cms
```

## Automatic Migrations

Migrations run automatically when the container starts:

1. Container waits for database (up to 60 seconds)
2. Checks which migrations have been applied
3. Runs only missing migrations
4. Records applied migrations in `schema_version` table
5. Starts the application

**Safe to restart** - Migrations won't re-run if already applied.

## Health Checks

```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' chatter-app

# Check via API
curl http://localhost:8000/health

# View health logs
docker inspect --format='{{range .State.Health.Log}}{{.Output}}{{end}}' chatter-app
```

## Troubleshooting

### Container won't start
```bash
docker-compose logs app
```

### Database connection failed
```bash
# Check if postgres is running
docker-compose ps

# Test connection
docker-compose exec app python3 -c "import psycopg2; import os; print(psycopg2.connect(os.getenv('DATABASE_URL')))"
```

### Migration failed
```bash
# View migration logs
docker-compose logs app | grep migration

# Check applied migrations
make db-shell
SELECT * FROM schema_version;
```

## Security Notes

- ✅ Runs as non-root user (UID 1000)
- ✅ Multi-stage build (smaller attack surface)
- ✅ No secrets in image (use environment variables)
- ✅ Health checks enabled
- ⚠️  Set strong SECRET_KEY and DB_PASSWORD
- ⚠️  Use HTTPS in production (configure reverse proxy)

## Architecture

```
┌─────────────────────────────────────┐
│  nginx (optional)                   │
│  Port 80/443                        │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│  chatter-app                        │
│  Port 8000                          │
│  - FastAPI application              │
│  - Auto migrations on startup       │
│  - Health checks                    │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│  postgres                           │
│  Port 5432 (internal)               │
│  or external DB (192.168.2.3:5433) │
└─────────────────────────────────────┘
```

## Files

- `Dockerfile` - Multi-stage production image
- `docker-compose.yml` - Container orchestration
- `docker-entrypoint.sh` - Startup script with migrations
- `.dockerignore` - Excluded files
- `.env.docker` - Environment template
- `Makefile` - Helper commands

## Support

- Full docs: [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)
- Troubleshooting: [TROUBLESHOOTING_DB.md](TROUBLESHOOTING_DB.md)
- Deployment tasks: [design/deployment_tasks.md](design/deployment_tasks.md)
