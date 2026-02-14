# Chatter

A social plugin for kevsrobots.com

---

## Quick Start with Docker

### Production Deployment

```bash
# 1. Create .env file with your configuration
cp app/.env.example .env
# Edit .env with your database credentials

# 2. Start the application
docker compose up -d

# 3. Check logs
docker compose logs -f app

# 4. Verify it's running
curl http://localhost:8006/health
```

### Development with Local Database

```bash
# Use the development compose file with bundled PostgreSQL
docker compose -f docker-compose.dev.yml up -d
```

---

## Database documentation

Database documentation is available at:

https://dbdocs.io/kevinmcaleer/Chatter

---

## Configuration

Create a `.env` file with the following variables:

```env
# Application
SECRET_KEY=your_secret_key_here
PORT=8006
ENVIRONMENT=production

# Database (for external PostgreSQL)
DB_HOST=192.168.2.3
DB_PORT=5433
DB_NAME=kevsrobots_cms
DB_USER=your_username_url_encoded
DB_PASSWORD=your_password_url_encoded

# CORS
ALLOWED_ORIGINS=https://yourdomain.com
```
