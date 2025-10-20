#!/bin/bash

# Test Chatter API
# This script tests the account management API endpoints

BASE_URL="http://127.0.0.1:8000"
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "🧪 Testing Chatter Account Management API"
echo "=========================================="
echo ""

# Test 1: Register a new account
echo -e "${BLUE}Test 1: Register New Account${NC}"
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/accounts/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "firstname": "Test",
    "lastname": "User",
    "email": "test@example.com",
    "password": "password123"
  }')

if echo "$REGISTER_RESPONSE" | grep -q "username"; then
    echo -e "${GREEN}✅ Registration successful${NC}"
    echo "$REGISTER_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$REGISTER_RESPONSE"
else
    echo -e "${RED}❌ Registration failed${NC}"
    echo "$REGISTER_RESPONSE"
fi
echo ""

# Test 2: Login
echo -e "${BLUE}Test 2: Login${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=password123")

TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ ! -z "$TOKEN" ]; then
    echo -e "${GREEN}✅ Login successful${NC}"
    echo "Token: ${TOKEN:0:20}..."
else
    echo -e "${RED}❌ Login failed${NC}"
    echo "$LOGIN_RESPONSE"
    exit 1
fi
echo ""

# Test 3: Get Account Info
echo -e "${BLUE}Test 3: Get Account Information${NC}"
ACCOUNT_RESPONSE=$(curl -s -X GET "$BASE_URL/accounts/me" \
  -H "Authorization: Bearer $TOKEN")

if echo "$ACCOUNT_RESPONSE" | grep -q "testuser"; then
    echo -e "${GREEN}✅ Account info retrieved${NC}"
    echo "$ACCOUNT_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$ACCOUNT_RESPONSE"
else
    echo -e "${RED}❌ Failed to get account info${NC}"
    echo "$ACCOUNT_RESPONSE"
fi
echo ""

# Test 4: Update Account
echo -e "${BLUE}Test 4: Update Account${NC}"
UPDATE_RESPONSE=$(curl -s -X PATCH "$BASE_URL/accounts/me" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "firstname": "Updated",
    "lastname": "Name"
  }')

if echo "$UPDATE_RESPONSE" | grep -q "Updated"; then
    echo -e "${GREEN}✅ Account updated${NC}"
    echo "$UPDATE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$UPDATE_RESPONSE"
else
    echo -e "${RED}❌ Failed to update account${NC}"
    echo "$UPDATE_RESPONSE"
fi
echo ""

# Test 5: Check Account Logs
echo -e "${BLUE}Test 5: Verify Logging (checking database)${NC}"
if [ -f "data/database.db" ]; then
    LOG_COUNT=$(sqlite3 data/database.db "SELECT COUNT(*) FROM accountlog WHERE user_id = (SELECT id FROM user WHERE username='testuser');" 2>/dev/null)
    if [ ! -z "$LOG_COUNT" ] && [ "$LOG_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✅ Account logs created: $LOG_COUNT entries${NC}"
    else
        echo -e "${RED}❌ No account logs found${NC}"
    fi
else
    echo -e "${BLUE}ℹ️  Database file not found (might be using PostgreSQL)${NC}"
fi
echo ""

echo "=========================================="
echo -e "${GREEN}✅ API Testing Complete!${NC}"
echo ""
echo "To test the UI:"
echo "  1. Keep the server running"
echo "  2. Open http://127.0.0.1:8000/docs for API documentation"
echo "  3. For Jekyll pages, serve from pages/ directory"
