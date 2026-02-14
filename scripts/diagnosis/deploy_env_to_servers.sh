#!/bin/bash
# Deploy correct .env file to Chatter servers
# Run this from your local machine

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "==================================================================="
echo "Deploy .env to Chatter Servers"
echo "==================================================================="
echo ""

# Check if local .env exists
if [ ! -f .env ]; then
    echo -e "${RED}✗ .env file not found in current directory${NC}"
    echo "Please run this script from the Chatter project root"
    exit 1
fi

echo -e "${GREEN}✓ Found local .env file${NC}"
echo ""

# Verify DATABASE_URL
echo "Verifying DATABASE_URL configuration..."
if grep -q "^DATABASE_URL=postgresql://Hd4AZn%3ANlSpH:8%260%2B6849Mx%23S@192.168.2.3:5433/kevsrobots_cms" .env; then
    echo -e "${GREEN}✓ DATABASE_URL looks correct${NC}"
else
    echo -e "${YELLOW}⚠ DATABASE_URL may not be correct${NC}"
    echo "Current DATABASE_URL:"
    grep "^DATABASE_URL=" .env | sed 's/:\/\/[^:]*:[^@]*@/:\/\/***:***@/'
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
echo ""

# List of Chatter servers
SERVERS=("192.168.2.2")
# Add more servers if needed:
# SERVERS=("192.168.2.1" "192.168.2.2")

# Remote path where Chatter is deployed
REMOTE_PATH="/home/kev/chatter"  # Adjust this to your actual deployment path

echo "Target servers:"
for server in "${SERVERS[@]}"; do
    echo "  - $server:$REMOTE_PATH"
done
echo ""

read -p "Deploy .env to these servers? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 0
fi
echo ""

# Deploy to each server
for server in "${SERVERS[@]}"; do
    echo "==================================================================="
    echo "Deploying to $server..."
    echo "==================================================================="

    # Backup existing .env on remote server
    echo "1. Backing up existing .env..."
    ssh kev@$server "cd $REMOTE_PATH && [ -f .env ] && cp .env .env.backup.\$(date +%Y%m%d_%H%M%S) || true" 2>&1

    # Copy new .env
    echo "2. Copying new .env..."
    scp .env kev@$server:$REMOTE_PATH/.env

    # Verify
    echo "3. Verifying..."
    ssh kev@$server "cd $REMOTE_PATH && grep '^DATABASE_URL=' .env | sed 's/:\/\/[^:]*:[^@]*@/:\/\/***:***@/'"

    # Restart application
    echo "4. Restarting Chatter application..."
    if ssh kev@$server "docker ps | grep -q chatter" 2>/dev/null; then
        echo "   Restarting Docker container..."
        ssh kev@$server "cd $REMOTE_PATH && docker-compose restart" || true
    elif ssh kev@$server "pgrep -f 'uvicorn.*main:app'" 2>/dev/null; then
        echo "   Restarting uvicorn process..."
        ssh kev@$server "sudo systemctl restart chatter" || echo "   Manual restart may be required"
    else
        echo "   ${YELLOW}⚠ Could not detect running application${NC}"
        echo "   You may need to manually restart the Chatter application"
    fi

    echo -e "${GREEN}✓ Deployment to $server complete${NC}"
    echo ""
done

echo "==================================================================="
echo "Deployment Complete!"
echo "==================================================================="
echo ""
echo "Next steps:"
echo "1. Verify connections by checking application logs on each server"
echo "2. Test the application by visiting https://kevsrobots.com"
echo "3. Monitor for any database connection errors"
echo ""
echo "To check logs on a server:"
echo "  ssh kev@192.168.2.2"
echo "  docker logs -f \$(docker ps --filter name=chatter -q)"
echo ""
