#!/bin/bash
# Backend diagnostics script for Chatter production issues

echo "=== Chatter Backend Diagnostics ==="
echo ""
echo "Date: $(date)"
echo ""

echo "1. Container Status:"
ssh DEV01 'docker ps | grep chatter'
echo ""

echo "2. Container Uptime and Restart Count:"
ssh DEV01 'docker inspect chatter-app --format "{{.State.Status}} | Started: {{.State.StartedAt}} | Restarts: {{.RestartCount}}"'
echo ""

echo "3. Container Resource Usage:"
ssh DEV01 'docker stats --no-stream chatter-app'
echo ""

echo "4. Recent Container Logs (last 50 lines):"
ssh DEV01 'docker logs chatter-app --tail 50'
echo ""

echo "5. Check for Python/Uvicorn errors:"
ssh DEV01 'docker logs chatter-app --tail 200 | grep -i "error\|exception\|traceback" | tail -20'
echo ""

echo "6. Check for slow database queries:"
ssh DEV01 'docker logs chatter-app --tail 200 | grep -i "slow\|timeout" | tail -20'
echo ""

echo "7. Database connections from container:"
ssh DEV01 'docker exec chatter-app bash -c "ps aux | grep -i postgres || echo No postgres connections found"'
echo ""

echo "8. Test database connectivity from container:"
ssh DEV01 'docker exec chatter-app python3 -c "
from app.database import get_session
from sqlmodel import text
import time

start = time.time()
try:
    session = next(get_session())
    result = session.exec(text(\"SELECT 1\")).first()
    elapsed = time.time() - start
    print(f\"✓ Database connection OK ({elapsed:.2f}s)\")
except Exception as e:
    elapsed = time.time() - start
    print(f\"✗ Database connection FAILED after {elapsed:.2f}s: {e}\")
"'
echo ""

echo "9. Test API endpoint response time:"
for i in {1..3}; do
  echo "  Test $i:"
  curl -s -o /dev/null -w "  HTTP: %{http_code}, Time: %{time_total}s\n" 'https://chatter.kevsrobots.com/health'
done
echo ""

echo "=== End Diagnostics ==="
