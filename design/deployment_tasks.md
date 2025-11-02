# Deployment Tasks for Account Management System

This document tracks all tasks that must be completed before deploying the account management system to production on kevsrobots.

## Summary

**Progress as of 2025-10-22:**
- ✅ **Critical Security Items Completed**: 7 of 11 critical tasks done
- ✅ **Password strength validation** implemented (8+ chars, uppercase, lowercase, numbers)
- ✅ **Rate limiting** added to sensitive endpoints (login, registration, password reset)
- ✅ **CORS configured** for cross-origin requests
- ✅ **Secure cookies** configured for production (HTTPS-only when ENVIRONMENT=production)
- ✅ **Database connection pooling** implemented with production settings
- ✅ **Code quality fixes** (duplicate code removed, deprecated endpoints marked)
- ✅ **PostgreSQL database live** - Connected to 192.168.2.3:5433, migrations applied, admin user created
- ✅ **Docker deployment ready** - Dockerfile, docker-compose, automatic migrations on startup
- 📝 **Remaining**: Email verification, account lockout, monitoring setup

## Status Legend
- [ ] Not started
- [IP] In progress
- [x] Completed
- [BLOCKED] Blocked/waiting

---

## 🔴 CRITICAL - Must Fix Before Production

### Security Configuration

- [x] **Rotate SECRET_KEY and store securely**
  - ✅ Generated new cryptographically secure secret key
  - ✅ Removed old SECRET_KEY from app/.env file
  - ✅ Added to environment variable configuration
  - ✅ .env already in .gitignore
  - ✅ Created .env.example template
  - **NEXT**: Set real SECRET_KEY in production environment

- [BLOCKED] **Configure PostgreSQL credentials**
  - Waiting for real credentials for postgresql://192.168.2.1:5433/kevsrobots_cms
  - ✅ Configuration ready in app/.env (commented out)
  - Location: app/.env:9
  - **ACTION NEEDED**: Get PostgreSQL username and password from sysadmin

- [x] **Enable HTTPS and secure cookies**
  - ✅ Cookie secure flag set based on ENVIRONMENT variable
  - ✅ Updated cookie settings in app/auth.py:112-119 and 208-214
  - **NEXT**: Set ENVIRONMENT=production in production
  - **NEXT**: Configure reverse proxy (nginx/Caddy) with SSL/TLS

- [x] **Add rate limiting**
  - ✅ Installed slowapi middleware
  - ✅ Added rate limits to login endpoint (5/minute) - app/auth.py:92
  - ✅ Added rate limits to registration endpoint (3/hour) - app/accounts.py:41
  - ✅ Added rate limits to password reset endpoint (5/hour) - app/accounts.py:195
  - ✅ Configured to disable in testing mode
  - ✅ Added slowapi to requirements.txt

- [x] **Implement password strength validation**
  - ✅ Added password strength validation to schemas
  - ✅ Minimum 8 characters
  - ✅ Requires uppercase, lowercase, and numbers
  - ✅ Validates on registration and password change
  - ✅ Returns clear error messages via Pydantic
  - Location: app/schemas.py:14-32, 83-95, 100-112

- [x] **Configure CORS for Jekyll site**
  - ✅ Added CORS middleware to app/main.py:26-32
  - ✅ Configured via ALLOWED_ORIGINS environment variable
  - ✅ Default localhost origins for development
  - **NEXT**: Set ALLOWED_ORIGINS=https://kevsrobots.com in production

### Database Issues

- [x] **Apply database migrations to PostgreSQL**
  - ✅ Migrations run automatically via docker-entrypoint.sh
  - ✅ 001_add_account_management_with_logging.sql
  - ✅ 002_add_last_login_tracking.sql
  - ✅ 003_add_force_password_reset.sql (admin password reset)
  - ✅ Schema matches database.dbml
  - **NEXT**: Verify schema_version table on production database

- [x] **Fix data model inconsistency in auth.py**
  - ✅ Updated /auth/register endpoint (app/auth.py:58-86)
  - ✅ Added firstname and lastname fields to match schema
  - ✅ Marked as deprecated in favor of /accounts/register
  - ✅ Updated templates/register.html with new fields
  - ✅ Updated register-page handler with all fields (app/auth.py:133-176)

- [x] **Fix duplicate delete logic**
  - ✅ Removed duplicate lines in app/auth.py:260-280
  - ✅ Account deletion flow tested
  - Location: app/auth.py:260-280

- [x] **Configure database connection pooling**
  - ✅ Added pool_size and max_overflow to create_engine()
  - ✅ Disabled echo=True in production mode
  - ✅ Added pool_pre_ping and pool_recycle settings
  - ✅ Environment-based configuration (ENVIRONMENT variable)
  - Location: app/database.py:14-41

### Missing Security Features

- [ ] **Implement email verification**
  - Add email_verified field to User model
  - Create verification token system
  - Send verification emails on registration
  - Prevent login until verified (optional)
  - Add resend verification endpoint

- [ ] **Add account lockout after failed logins**
  - Track failed login attempts
  - Lock account after N failed attempts (e.g., 5)
  - Add unlock mechanism (time-based or admin)
  - Log lockout events

---

## 🟡 HIGH PRIORITY - Strongly Recommended

### Monitoring & Logging

- [ ] **Add structured application logging**
  - Install logging framework (structlog or similar)
  - Log failed login attempts with IP and timestamp
  - Log database errors
  - Log API errors and exceptions
  - Configure log levels for production
  - Set up log rotation

- [ ] **Add health check endpoint**
  - Create /health endpoint
  - Check database connectivity
  - Check Redis/cache connectivity (if used)
  - Return 200 if healthy, 503 if unhealthy
  - Add to uptime monitoring

- [ ] **Set up error tracking**
  - Configure Sentry or similar service
  - Add to app/main.py
  - Test error reporting
  - Set up alerts for critical errors

### Data Privacy & Compliance

- [ ] **Create privacy policy**
  - Document what data is collected (IP, user agent, email, etc.)
  - Explain how data is used
  - Explain data retention periods
  - Add link to privacy policy in registration flow
  - Host on kevsrobots site

- [ ] **Create terms of service**
  - Define acceptable use
  - Account termination conditions
  - Add link to ToS in registration flow
  - Host on kevsrobots site

- [ ] **Document data retention policy**
  - How long are account logs kept?
  - What happens to deleted user data?
  - Implement automated cleanup if needed
  - GDPR compliance if serving EU users

- [ ] **Add GDPR compliance features (if needed)**
  - Right to access data (export account data)
  - Right to be forgotten (complete data deletion)
  - Cookie consent banner
  - Data processing agreement

### Performance & Scalability

- [ ] **Optimize database queries**
  - Review account page queries (app/auth.py:163-165)
  - Add eager loading where appropriate
  - Add database indexes for common queries
  - Test query performance with large datasets

- [ ] **Add caching layer (optional)**
  - Set up Redis for session management
  - Cache frequently accessed data
  - Implement rate limiting with Redis
  - Configure cache TTLs

---

## 🟢 NICE TO HAVE - Future Improvements

### Features

- [ ] **Password reset via email**
  - Generate secure reset tokens
  - Send reset emails
  - Create reset password form
  - Add expiration to reset tokens

- [ ] **Two-factor authentication (2FA)**
  - Add TOTP support
  - QR code generation for setup
  - Backup codes
  - Optional vs required for different user types

- [ ] **Session management**
  - View active sessions
  - Revoke sessions
  - Device fingerprinting
  - Last accessed timestamps

- [ ] **Account data export**
  - GDPR right to data portability
  - Export user data as JSON
  - Include all associated data (comments, likes, logs)

### Testing

- [ ] **Integration tests with PostgreSQL**
  - Test suite against real PostgreSQL
  - Test migrations
  - Test edge cases with production database

- [ ] **Load testing**
  - Use locust or similar tool
  - Simulate expected traffic
  - Identify bottlenecks
  - Test rate limiting

- [ ] **Security penetration testing**
  - SQL injection testing
  - XSS testing
  - CSRF testing
  - Authentication bypass testing

### Documentation

- [ ] **API documentation**
  - Ensure FastAPI /docs endpoint is accessible
  - Add usage examples
  - Document authentication flow
  - Document error codes

- [ ] **Admin user guide**
  - How to create admin users
  - How to use admin endpoints
  - Common administrative tasks
  - Troubleshooting guide

- [ ] **Incident response procedures**
  - Security incident response plan
  - Data breach notification process
  - System recovery procedures
  - Contact information for emergencies

---

## 📋 Pre-Deployment Verification

### Final Checks Before Going Live

- [ ] All critical (🔴) tasks completed
- [ ] All high priority (🟡) tasks completed or explicitly deferred
- [ ] Staging environment tested successfully
- [ ] Backup and restore procedures tested
- [ ] Rollback plan documented and tested
- [ ] Monitoring and alerts configured
- [ ] Team trained on new system
- [ ] Documentation updated
- [ ] Security review completed
- [ ] Performance testing completed

---

## Deployment Steps

1. [ ] Deploy to staging environment
2. [ ] Run smoke tests on staging
3. [ ] Apply database migrations to production
4. [ ] Deploy application to production
5. [ ] Verify health check endpoint
6. [ ] Monitor logs for errors
7. [ ] Test critical user flows
8. [ ] Monitor performance metrics
9. [ ] Have rollback ready if needed

---

## Post-Deployment

- [ ] Monitor error rates for 24 hours
- [ ] Check database performance
- [ ] Verify backup jobs running
- [ ] Review security logs
- [ ] Gather user feedback
- [ ] Document any issues encountered
- [ ] Update this document with lessons learned

---

**Last Updated:** 2025-10-22
**Maintained By:** Development Team

---

## 🐳 Docker Deployment (Issue #31)

### Docker Configuration

- [x] **Create Dockerfile**
  - ✅ Multi-stage build for optimized image size
  - ✅ Runs as non-root user (UID 1000)
  - ✅ Health checks included
  - ✅ PostgreSQL client for migrations
  - Location: `Dockerfile`

- [x] **Create docker-compose.yml**
  - ✅ Application service configuration
  - ✅ Optional PostgreSQL service
  - ✅ Optional nginx reverse proxy
  - ✅ Volume mounts for data and logs
  - ✅ Health check dependencies
  - Location: `docker-compose.yml`

- [x] **Create migration system**
  - ✅ schema_version table for tracking migrations
  - ✅ Automatic migration on container startup
  - ✅ Idempotent - safe to restart containers
  - ✅ Migrations won't re-run if already applied
  - Location: `docker-entrypoint.sh`, `migrations/versions/schema_version.sql`

- [x] **Create environment configuration**
  - ✅ .env.docker template with all variables
  - ✅ .dockerignore for excluding files
  - ✅ Documentation for external vs internal DB
  - Location: `.env.docker`, `.dockerignore`

- [x] **Create deployment helpers**
  - ✅ Makefile with common Docker commands
  - ✅ Build, run, logs, shell, backup commands
  - ✅ Production push to local registry (192.168.2.1:5000)
  - Location: `Makefile`

- [x] **Create documentation**
  - ✅ Full deployment guide (DOCKER_DEPLOYMENT.md)
  - ✅ Quick reference (README.Docker.md)
  - ✅ Troubleshooting section
  - ✅ Migration system explanation

### Docker Deployment Steps

1. [x] **Build image**
   ```bash
   make build
   # or: docker build -t chatter:latest .
   ```

2. [ ] **Configure environment**
   ```bash
   cp .env.docker .env
   # Edit .env with production values
   ```

3. [ ] **Test locally**
   ```bash
   make run
   make logs
   curl http://localhost:8000/health
   ```

4. [ ] **Push to registry** (if using 192.168.2.1:5000)
   ```bash
   make deploy-prod
   ```

5. [ ] **Deploy on production server**
   ```bash
   docker pull 192.168.2.1:5000/kevsrobots/chatter:latest
   docker-compose up -d
   ```

### Migration System Features

The Docker deployment includes an intelligent migration system:

**Features:**
- Waits for database to be ready (up to 60 seconds)
- Checks `schema_version` table for applied migrations
- Runs only missing migrations
- Records each migration with timestamp
- Idempotent - safe to restart multiple times
- No manual migration steps needed

**How it works:**
1. Container starts → `docker-entrypoint.sh` executes
2. Waits for database connection
3. Creates `schema_version` table if needed
4. Checks which migrations are applied
5. Runs missing migrations in order
6. Starts FastAPI application

**Migrations tracked:**
- `schema_version` - Version tracking table itself
- `000_create_initial_schema` - All tables (user, accountlog, like, comment)
- `001_add_account_management_with_logging` - Account management and logging
- `002_add_last_login_tracking` - Last login timestamps
- `003_add_force_password_reset` - Admin password reset functionality

### Docker Registry Setup

**Using local registry (192.168.2.1:5000):**

```bash
# On development machine
make deploy-prod

# On production server
docker pull 192.168.2.1:5000/kevsrobots/chatter:latest
docker tag 192.168.2.1:5000/kevsrobots/chatter:latest chatter:latest
docker-compose up -d
```

**Without registry (export/import):**

```bash
# Save image
docker save chatter:latest | gzip > chatter.tar.gz

# Transfer to server
scp chatter.tar.gz user@server:/tmp/

# Load on server
docker load < /tmp/chatter.tar.gz
docker-compose up -d
```

### Docker Health Checks

Built-in health monitoring:

```bash
# Check status
docker inspect --format='{{.State.Health.Status}}' chatter-app

# Should show: healthy
```

Health check hits `/health` endpoint every 30 seconds.

### Docker Security

- ✅ Runs as non-root user (chatter, UID 1000)
- ✅ Multi-stage build (minimal attack surface)
- ✅ No secrets in image (uses environment variables)
- ✅ Minimal dependencies
- ✅ Health checks for monitoring
- ✅ Read-only filesystem option available

### Next Steps for Docker Deployment

1. [ ] Test Docker build completes successfully
2. [ ] Test with external PostgreSQL database
3. [ ] Verify migrations run on first start
4. [ ] Verify migrations don't re-run on restart
5. [ ] Set up local registry at 192.168.2.1:5000
6. [ ] Configure nginx reverse proxy (optional)
7. [ ] Set up SSL certificates for HTTPS
8. [ ] Configure automated backups
9. [ ] Set up monitoring/alerting
10. [ ] Document rollback procedures

---

## 📁 NAS Storage Configuration (Issue #44 - User Profiles)

### Profile Picture Storage

Profile pictures are stored on NAS (SMB share) with local fallback:

**Storage Priority:**
1. **Primary**: NAS at 192.168.1.79/chatter/profile_pictures
2. **Fallback**: Local container storage at /tmp/chatter_uploads/profile_pictures

**Features:**
- Automatic fallback if NAS unavailable
- Files served from NAS when available
- Supports SMB/CIFS protocol
- Image validation and resizing (400x400px max, 5MB limit)

### NAS Configuration Steps

- [x] **Add NAS credentials to .env**
  - ✅ Added to .env.example template
  - ✅ NAS_HOST=192.168.1.79
  - ✅ NAS_USERNAME (set in environment)
  - ✅ NAS_PASSWORD (set in environment)
  - ✅ NAS_SHARE_NAME=chatter
  - Location: `.env.example:49-56`, `.env:40-47`

- [x] **Install SMB client library**
  - ✅ Added smbprotocol==1.14.0 to requirements.txt
  - ✅ Included in Docker image build
  - Location: `requirements.txt:63`

- [x] **Implement NAS storage layer**
  - ✅ Created storage.py with NAS read/write/delete functions
  - ✅ Connection pooling and error handling
  - ✅ Automatic fallback to local storage
  - ✅ Image validation and resizing
  - Location: `app/storage.py`

- [x] **Update profile picture endpoints**
  - ✅ Upload endpoint saves to NAS (profile.py:upload_profile_picture)
  - ✅ Delete endpoint removes from NAS (profile.py:delete_profile_picture)
  - ✅ Serve endpoint reads from NAS first (profile.py:serve_profile_picture)
  - Location: `app/profile.py:292-330`

- [x] **Create migration script**
  - ✅ Script to move existing files from containers to NAS
  - ✅ Connects to all production servers (dev01, dev03, dev04)
  - ✅ Extracts files from /tmp/chatter_uploads/profile_pictures
  - ✅ Uploads to NAS with verification
  - Location: `migrate_profile_pictures_to_nas.py`

- [x] **Create test script**
  - ✅ Test NAS connectivity
  - ✅ Test file upload/read/delete operations
  - ✅ Cleanup test files
  - Location: `test_nas_connection.py`

### NAS Deployment Steps

1. [ ] **Configure NAS share**
   ```bash
   # On NAS (192.168.1.79)
   # Create SMB share named "chatter"
   # Create directory: chatter/profile_pictures
   # Set permissions for kevsrobots user
   ```

2. [ ] **Update production .env files**
   ```bash
   # On each server (dev01, dev03, dev04)
   # Add to /path/to/chatter/.env:
   NAS_HOST=192.168.1.79
   NAS_USERNAME=kevsrobots
   NAS_PASSWORD=<password>
   NAS_SHARE_NAME=chatter
   ```

3. [ ] **Test NAS connectivity**
   ```bash
   # Inside Docker container
   docker exec chatter-app python test_nas_connection.py
   ```

4. [ ] **Run migration script** (if existing pictures)
   ```bash
   # On development machine (with SSH access to servers)
   python migrate_profile_pictures_to_nas.py
   ```

5. [ ] **Verify profile pictures**
   ```bash
   # Check that existing profile pictures still display
   # Upload new profile picture and verify it saves to NAS
   # Delete profile picture and verify removal from NAS
   ```

### NAS Troubleshooting

**If NAS is unavailable:**
- App automatically falls back to local storage
- New uploads save to /tmp/chatter_uploads/profile_pictures
- Existing NAS files won't be accessible until NAS restored
- No errors shown to users, logging shows fallback

**If NAS credentials are wrong:**
- Check logs: `docker logs chatter-app | grep NAS`
- Verify .env file has correct credentials
- Test connection: `docker exec chatter-app python test_nas_connection.py`
- Update .env and restart: `docker-compose restart`

**To manually check NAS files:**
```bash
# On any server with SMB client
smbclient //192.168.1.79/chatter -U kevsrobots
cd profile_pictures
ls
```

### NAS Monitoring

Monitor NAS storage health:
- Check logs for "Failed to connect to NAS" warnings
- Verify profile pictures display correctly on user profiles
- Monitor NAS disk space usage
- Set up alerts for NAS connectivity issues

