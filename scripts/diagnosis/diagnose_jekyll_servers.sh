#!/bin/bash

# Diagnose Jekyll server health across DEV01-DEV04
# Check which server is causing 502/522 errors

echo "=== Jekyll Server Health Diagnostics ==="
echo "Checking servers: DEV01-DEV04 (192.168.2.1-4)"
echo ""

SERVERS=("192.168.2.1" "192.168.2.2" "192.168.2.3" "192.168.2.4")
NAMES=("DEV01" "DEV02" "DEV03" "DEV04")

for i in "${!SERVERS[@]}"; do
    SERVER="${SERVERS[$i]}"
    NAME="${NAMES[$i]}"

    echo "========================================"
    echo "Server: $NAME ($SERVER)"
    echo "========================================"

    # Check if server is reachable
    if ! ping -c 1 -W 1 "$SERVER" > /dev/null 2>&1; then
        echo "❌ Server unreachable"
        echo ""
        continue
    fi

    echo "✓ Server reachable"

    # Check nginx container status
    echo ""
    echo "--- Nginx Container Status ---"
    sshpass -p "monkeybaby" ssh -o StrictHostKeyChecking=no kev@"$SERVER" 'docker ps --filter "name=nginx" --format "{{.Names}}: {{.Status}}" 2>/dev/null || echo "No nginx container found"'

    # Check Jekyll container status
    echo ""
    echo "--- Jekyll Container Status ---"
    sshpass -p "monkeybaby" ssh -o StrictHostKeyChecking=no kev@"$SERVER" 'docker ps --filter "name=jekyll" --format "{{.Names}}: {{.Status}}" 2>/dev/null || docker ps | grep 3333 || echo "No Jekyll container found"'

    # Check system load
    echo ""
    echo "--- System Load ---"
    sshpass -p "monkeybaby" ssh -o StrictHostKeyChecking=no kev@"$SERVER" 'uptime'

    # Check memory usage
    echo ""
    echo "--- Memory Usage ---"
    sshpass -p "monkeybaby" ssh -o StrictHostKeyChecking=no kev@"$SERVER" 'free -h | grep -E "Mem:|Swap:"'

    # Check disk usage
    echo ""
    echo "--- Disk Usage ---"
    sshpass -p "monkeybaby" ssh -o StrictHostKeyChecking=no kev@"$SERVER" 'df -h / | tail -1'

    # Test Jekyll response time
    echo ""
    echo "--- Jekyll Response Time Test (port 3333) ---"
    START=$(date +%s%N)
    RESPONSE=$(sshpass -p "monkeybaby" ssh -o StrictHostKeyChecking=no kev@"$SERVER" 'curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:3333/ 2>/dev/null || echo "TIMEOUT"')
    END=$(date +%s%N)
    DURATION=$(( (END - START) / 1000000 ))

    if [ "$RESPONSE" = "TIMEOUT" ]; then
        echo "❌ Request timed out (>5s)"
    else
        echo "HTTP Status: $RESPONSE"
        echo "Response time: ${DURATION}ms"

        if [ "$DURATION" -gt 2000 ]; then
            echo "⚠️  SLOW RESPONSE (>2s)"
        elif [ "$DURATION" -gt 1000 ]; then
            echo "⚠️  Moderate response time (>1s)"
        else
            echo "✓ Good response time"
        fi
    fi

    # Check recent nginx errors
    echo ""
    echo "--- Recent Nginx Error Log (last 10 errors) ---"
    sshpass -p "monkeybaby" ssh -o StrictHostKeyChecking=no kev@"$SERVER" 'docker exec nginx tail -20 /var/log/nginx/error.log 2>/dev/null | grep -i error | tail -10 || echo "No errors found or nginx not accessible"'

    echo ""
done

echo "========================================"
echo "Checking Load Balancer (192.168.1.4)"
echo "========================================"

# Check load balancer nginx logs for upstream failures
echo "--- Recent Upstream Failures (last 20) ---"
sshpass -p "monkeybaby" ssh -o StrictHostKeyChecking=no kev@192.168.1.4 'docker exec nginx tail -200 /var/log/nginx/error.log 2>/dev/null | grep -E "upstream|timed out|502|504" | tail -20 || echo "No nginx logs accessible"'

echo ""
echo "--- Load Balancer Upstream Status ---"
sshpass -p "monkeybaby" ssh -o StrictHostKeyChecking=no kev@192.168.1.4 'docker exec nginx tail -100 /var/log/nginx/access.log 2>/dev/null | grep -E "192\.168\.2\.[2-4]:3333" | tail -20 || echo "No access logs"'

echo ""
echo "=== Diagnostics Complete ==="
