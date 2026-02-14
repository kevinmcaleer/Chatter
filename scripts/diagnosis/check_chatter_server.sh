#!/bin/bash
# Diagnostic script for Chatter server configuration
# Run this ON a Chatter server (192.168.2.2, etc.)

echo "==================================================================="
echo "Chatter Server Configuration Check"
echo "==================================================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Check if .env file exists
echo "1. Checking for .env file..."
if [ -f .env ]; then
    echo -e "${GREEN}✓ .env file found${NC}"
    echo "Location: $(pwd)/.env"
    echo "Permissions: $(ls -l .env | awk '{print $1, $3, $4}')"
else
    echo -e "${RED}✗ .env file NOT found in current directory${NC}"
    echo "Current directory: $(pwd)"
    echo "Please run this script from the Chatter application directory"
fi
echo ""

# 2. Check DATABASE_URL (without exposing password)
echo "2. Checking DATABASE_URL configuration..."
if [ -f .env ]; then
    DB_URL=$(grep "^DATABASE_URL=" .env | cut -d'=' -f2-)
    if [ -n "$DB_URL" ]; then
        echo -e "${GREEN}✓ DATABASE_URL is set${NC}"
        # Show URL with password masked
        MASKED_URL=$(echo "$DB_URL" | sed 's/:\/\/[^:]*:[^@]*@/:\/\/***:***@/')
        echo "DATABASE_URL: $MASKED_URL"

        # Parse and validate components
        echo ""
        echo "Parsed components:"
        echo "  Host: $(echo "$DB_URL" | grep -oP '(?<=@)[^:]+(?=:)' || echo 'NOT FOUND')"
        echo "  Port: $(echo "$DB_URL" | grep -oP '(?<=:)\d+(?=/)' || echo 'NOT FOUND')"
        echo "  Database: $(echo "$DB_URL" | grep -oP '(?<=/)[^?]+' || echo 'NOT FOUND')"
    else
        echo -e "${RED}✗ DATABASE_URL not found in .env${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Skipped (no .env file)${NC}"
fi
echo ""

# 3. Test database connection using Python
echo "3. Testing database connection with Python..."
cat > /tmp/test_db_conn.py << 'EOFPYTHON'
import os
from urllib.parse import urlparse, unquote

# Try to load .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ dotenv loaded")
except ImportError:
    print("⚠ python-dotenv not installed, using environment variables only")

# Get DATABASE_URL
db_url = os.getenv('DATABASE_URL')
if not db_url:
    print("✗ DATABASE_URL not found in environment")
    exit(1)

print(f"✓ DATABASE_URL found")

# Parse URL
try:
    parsed = urlparse(db_url)
    print(f"  Scheme: {parsed.scheme}")
    print(f"  Host: {parsed.hostname}")
    print(f"  Port: {parsed.port}")
    print(f"  Database: {parsed.path.lstrip('/')}")
    print(f"  Username: {unquote(parsed.username) if parsed.username else 'NOT SET'}")
    print(f"  Password: {'***' if parsed.password else 'NOT SET'}")
except Exception as e:
    print(f"✗ Error parsing DATABASE_URL: {e}")
    exit(1)

# Test connection
try:
    import psycopg2

    # Decode URL-encoded username and password
    username = unquote(parsed.username) if parsed.username else None
    password = unquote(parsed.password) if parsed.password else None

    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port,
        database=parsed.path.lstrip('/'),
        user=username,
        password=password,
        connect_timeout=5
    )

    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]
    print(f"\n✓ Connection successful!")
    print(f"  PostgreSQL: {version[:50]}...")

    cur.close()
    conn.close()

except ImportError:
    print("\n⚠ psycopg2 not installed, cannot test connection")
    print("  Install with: pip install psycopg2-binary")
except Exception as e:
    print(f"\n✗ Connection failed!")
    print(f"  Error: {e}")
    exit(1)
EOFPYTHON

python3 /tmp/test_db_conn.py
echo ""

# 4. Check if Chatter application is running
echo "4. Checking if Chatter application is running..."
if docker ps | grep -q chatter; then
    echo -e "${GREEN}✓ Chatter container is running${NC}"
    echo ""
    echo "Container details:"
    docker ps --filter name=chatter --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

    echo ""
    echo "Container environment (DATABASE_URL):"
    docker exec $(docker ps --filter name=chatter -q | head -1) sh -c 'echo $DATABASE_URL | sed "s/:\/\/[^:]*:[^@]*@/:\/\/***:***@/"' 2>/dev/null || echo "  Could not retrieve"
elif pgrep -f "uvicorn.*main:app" > /dev/null; then
    echo -e "${GREEN}✓ Chatter process is running (uvicorn)${NC}"
    ps aux | grep "uvicorn.*main:app" | grep -v grep
else
    echo -e "${YELLOW}⚠ Chatter does not appear to be running${NC}"
fi
echo ""

# 5. Check recent application logs
echo "5. Checking recent application logs for database errors..."
if docker ps | grep -q chatter; then
    echo "Recent Docker logs:"
    docker logs $(docker ps --filter name=chatter -q | head -1) --tail 20 2>&1 | grep -i "database\|connection\|error" || echo "  No database errors found in recent logs"
elif [ -f logs/chatter.log ]; then
    echo "Recent application logs:"
    tail -20 logs/chatter.log | grep -i "database\|connection\|error" || echo "  No database errors found in recent logs"
else
    echo -e "${YELLOW}⚠ Could not find application logs${NC}"
fi
echo ""

# 6. Test connection from this server to database
echo "6. Testing direct connection to database server..."
if command -v psql &> /dev/null; then
    # Load credentials from .env if available
    if [ -f .env ]; then
        source <(grep "^DB_USER=" .env)
        source <(grep "^DB_PASSWORD=" .env)

        # URL decode username and password
        DB_USER_DECODED=$(python3 -c "import urllib.parse; print(urllib.parse.unquote('$DB_USER'))")
        DB_PASS_DECODED=$(python3 -c "import urllib.parse; print(urllib.parse.unquote('$DB_PASSWORD'))")

        echo "Attempting connection with credentials from .env..."
        PGPASSWORD="$DB_PASS_DECODED" psql -h 192.168.2.3 -p 5433 -U "$DB_USER_DECODED" -d kevsrobots_cms -c "SELECT 'Connection successful!' as status, current_user, current_database();" 2>&1
    else
        echo -e "${YELLOW}⚠ No .env file, cannot test connection${NC}"
    fi
else
    echo -e "${YELLOW}⚠ psql not installed${NC}"
    echo "Install with: sudo apt-get install postgresql-client"
fi
echo ""

echo "==================================================================="
echo "Diagnostic Complete"
echo "==================================================================="
echo ""
echo "If connection failed, check:"
echo "1. .env file exists and has correct DATABASE_URL"
echo "2. DATABASE_URL uses URL-encoded special characters"
echo "3. Application is reading the .env file"
echo "4. Docker container has correct environment variables"
echo ""
echo "Expected DATABASE_URL format:"
echo "DATABASE_URL=postgresql://Hd4AZn%3ANlSpH:8%260%2B6849Mx%23S@192.168.2.3:5433/kevsrobots_cms"
echo ""
