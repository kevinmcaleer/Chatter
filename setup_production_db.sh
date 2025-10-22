#!/bin/bash

# Production Database Setup Script
# This script helps you configure and initialize the PostgreSQL database

set -e  # Exit on error

echo "======================================"
echo "Production Database Setup for Chatter"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if .env file exists
if [ ! -f "app/.env" ]; then
    print_error ".env file not found!"
    echo "Please create app/.env file first"
    exit 1
fi

# Load DATABASE_URL from .env
source app/.env

if [ -z "$DATABASE_URL" ]; then
    print_error "DATABASE_URL not set in app/.env"
    echo ""
    echo "Please add your PostgreSQL credentials to app/.env:"
    echo "DATABASE_URL=postgresql://username:password@192.168.2.1:5433/kevsrobots_cms"
    exit 1
fi

print_success "DATABASE_URL found in .env"

# Test database connection
echo ""
echo "Step 1: Testing database connection..."
psql "$DATABASE_URL" -c "SELECT version();" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    print_success "Successfully connected to PostgreSQL database"
else
    print_error "Failed to connect to database"
    echo "Please check your DATABASE_URL credentials"
    exit 1
fi

# Show current tables
echo ""
echo "Step 2: Checking existing tables..."
EXISTING_TABLES=$(psql "$DATABASE_URL" -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;")
if [ -z "$EXISTING_TABLES" ]; then
    print_warning "No tables found in database"
else
    echo "Existing tables:"
    echo "$EXISTING_TABLES"
fi

# Check if user table exists
USER_TABLE_EXISTS=$(psql "$DATABASE_URL" -t -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'user');")

if [[ $USER_TABLE_EXISTS == *"t"* ]]; then
    print_success "Table 'user' already exists"

    # Check if it has the new fields
    HAS_FIRSTNAME=$(psql "$DATABASE_URL" -t -c "SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name='user' AND column_name='firstname');")

    if [[ $HAS_FIRSTNAME == *"f"* ]]; then
        print_warning "Table 'user' exists but missing new fields - migrations needed"
        NEEDS_MIGRATION=true
    else
        print_success "Table 'user' has new fields"
        NEEDS_MIGRATION=false
    fi
else
    print_warning "Table 'user' does not exist - full schema creation needed"
    NEEDS_MIGRATION=true
fi

# Ask user if they want to proceed
if [ "$NEEDS_MIGRATION" = true ]; then
    echo ""
    echo "Step 3: Apply database migrations"
    read -p "Do you want to apply the migrations now? (y/n) " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Applying migration 001: Account management with logging..."
        psql "$DATABASE_URL" -f migrations/versions/001_add_account_management_with_logging.sql

        if [ $? -eq 0 ]; then
            print_success "Migration 001 applied successfully"
        else
            print_error "Migration 001 failed"
            exit 1
        fi

        echo ""
        echo "Applying migration 002: Last login tracking..."
        psql "$DATABASE_URL" -f migrations/versions/002_add_last_login_tracking.sql

        if [ $? -eq 0 ]; then
            print_success "Migration 002 applied successfully"
        else
            print_error "Migration 002 failed"
            exit 1
        fi
    else
        echo "Skipping migrations"
        exit 0
    fi
fi

# Verify schema
echo ""
echo "Step 4: Verifying database schema..."
USER_COLUMNS=$(psql "$DATABASE_URL" -t -c "SELECT column_name FROM information_schema.columns WHERE table_name='user' ORDER BY column_name;")
echo "Columns in 'user' table:"
echo "$USER_COLUMNS"

ACCOUNTLOG_EXISTS=$(psql "$DATABASE_URL" -t -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'accountlog');")
if [[ $ACCOUNTLOG_EXISTS == *"t"* ]]; then
    print_success "Table 'accountlog' exists"
else
    print_error "Table 'accountlog' missing!"
fi

# Count existing users
USER_COUNT=$(psql "$DATABASE_URL" -t -c "SELECT COUNT(*) FROM \"user\";")
echo ""
echo "Current user count: $USER_COUNT"

# Ask if they want to create an admin user
if [ "$USER_COUNT" -gt 0 ]; then
    print_warning "Users already exist in database"
    read -p "Do you want to create an admin user anyway? (y/n) " -n 1 -r
    echo ""
    CREATE_ADMIN=$REPLY
else
    print_warning "No users in database"
    CREATE_ADMIN="y"
fi

if [[ $CREATE_ADMIN =~ ^[Yy]$ ]]; then
    echo ""
    echo "Step 5: Create admin user"
    echo "You can create an admin user via the API:"
    echo ""
    echo "curl -X POST http://localhost:8001/accounts/register \\"
    echo "  -H 'Content-Type: application/json' \\"
    echo "  -d '{"
    echo "    \"username\": \"admin\","
    echo "    \"firstname\": \"Admin\","
    echo "    \"lastname\": \"User\","
    echo "    \"email\": \"admin@kevsrobots.com\","
    echo "    \"password\": \"YourSecure123\"  # Must be 8+ chars with upper, lower, number"
    echo "  }'"
    echo ""
    echo "Then update the user type to admin with direct SQL:"
    echo "psql \"$DATABASE_URL\" -c \"UPDATE \\\"user\\\" SET type=1 WHERE username='admin';\""
    echo ""
fi

print_success "Database setup complete!"
echo ""
echo "Next steps:"
echo "1. Start your application with: uvicorn app.main:app --port 8001"
echo "2. Create an admin user using the curl command above"
echo "3. Test the API endpoints"
echo "4. Check design/deployment_tasks.md for remaining tasks"
