# Chatter Documentation

Comprehensive documentation for the Chatter authentication and account management system.

## Overview

Chatter is a FastAPI-based authentication service for the Kev's Robots ecosystem. It provides user registration, login, account management, and administrative features.

**Live URL:** https://chatter.kevsrobots.com

## Documentation Sections

### Core Functionality
- [**API Reference**](API.md) - Complete API endpoint documentation
- [**Authentication Flow**](AUTHENTICATION.md) - How authentication works
- [**Database Schema**](DATABASE.md) - Database structure and relationships

### Features
- [**User Management**](USER_MANAGEMENT.md) - Registration, login, account management
- [**Admin Features**](ADMIN.md) - Admin panel and administrative functions
- [**Password Reset**](PASSWORD_RESET.md) - One-time code password reset system

### Deployment & Configuration
- [**Deployment Guide**](DEPLOYMENT.md) - How to deploy Chatter
- [**Configuration**](CONFIGURATION.md) - Environment variables and settings
- [**Docker Setup**](DOCKER.md) - Docker deployment instructions

### Development
- [**Development Setup**](DEVELOPMENT.md) - Local development environment
- [**Testing**](TESTING.md) - Running tests
- [**Contributing**](CONTRIBUTING.md) - Development guidelines

## Quick Start

### For Users
1. Visit https://chatter.kevsrobots.com/register to create an account
2. Login at https://chatter.kevsrobots.com/login
3. Manage your account at https://chatter.kevsrobots.com/account

### For Administrators
1. Login with admin credentials
2. Access admin panel at https://chatter.kevsrobots.com/admin
3. Manage users, generate password reset codes, and more

### For Developers
```bash
# Clone repository
git clone https://github.com/kevinmcaleer/chatter.git
cd chatter

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run locally
uvicorn app.main:app --reload --port 8001
```

## Architecture

Chatter is built with:
- **Backend:** FastAPI (Python 3.13)
- **Database:** PostgreSQL
- **ORM:** SQLModel
- **Templates:** Jinja2
- **CSS:** Bootstrap 5.3.3
- **Deployment:** Docker + Docker Compose

## Key Features

✅ User registration and authentication
✅ JWT-based session management
✅ Secure HTTP-only cookies
✅ Admin panel for user management
✅ Password reset with one-time codes
✅ Rate limiting on sensitive endpoints
✅ Cross-domain authentication (kevsrobots.com ↔ chatter.kevsrobots.com)
✅ Account activity tracking
✅ Docker deployment with automatic migrations

## Security

- Passwords hashed with bcrypt
- JWT tokens with secure cookies
- HTTPS-only in production
- CORS configured for specific origins
- Rate limiting on login/registration
- Admin-only endpoints protected
- SQL injection protection via SQLModel

## Support

For issues or questions:
- GitHub Issues: https://github.com/kevinmcaleer/chatter/issues
- Documentation: https://github.com/kevinmcaleer/chatter/tree/main/docs

## License

See [LICENSE](../LICENSE) file for details.
