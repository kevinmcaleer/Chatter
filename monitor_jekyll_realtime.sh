#!/bin/bash

# Real-time monitoring of Jekyll servers
# Runs continuous health checks and logs slow/failed responses

echo "=== Real-time Jekyll Server Monitor ==="
echo "Press Ctrl+C to stop"
echo ""

SERVERS=("192.168.2.2" "192.168.2.3" "192.168.2.4")
NAMES=("DEV02" "DEV03" "DEV04")
LOG_FILE="/Users/kev/Python/Chatter/jekyll_health_log.txt"

# Clear previous log
echo "=== Jekyll Health Monitor Started at $(date) ===" > "$LOG_FILE"

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

    for i in "${!SERVERS[@]}"; do
        SERVER="${SERVERS[$i]}"
        NAME="${NAMES[$i]}"

        # Test response time
        START=$(date +%s%N)
        HTTP_CODE=$(sshpass -p "monkeybaby" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=2 kev@"$SERVER" 'curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:3333/ 2>/dev/null' || echo "SSH_FAIL")
        END=$(date +%s%N)
        DURATION=$(( (END - START) / 1000000 ))

        STATUS="✓"
        ALERT=""

        if [ "$HTTP_CODE" = "SSH_FAIL" ]; then
            STATUS="❌"
            ALERT="SSH_FAILED"
            echo "$TIMESTAMP - $NAME ($SERVER) - SSH FAILED" | tee -a "$LOG_FILE"
        elif [ "$HTTP_CODE" != "200" ]; then
            STATUS="❌"
            ALERT="HTTP_${HTTP_CODE}"
            echo "$TIMESTAMP - $NAME ($SERVER) - HTTP $HTTP_CODE (${DURATION}ms)" | tee -a "$LOG_FILE"
        elif [ "$DURATION" -gt 3000 ]; then
            STATUS="⚠️"
            ALERT="SLOW"
            echo "$TIMESTAMP - $NAME ($SERVER) - SLOW RESPONSE: ${DURATION}ms" | tee -a "$LOG_FILE"
        fi

        # Only log to console if there's an issue, otherwise just show a dot
        if [ -n "$ALERT" ]; then
            printf "%s %s %6dms %s\n" "$TIMESTAMP" "$NAME" "$DURATION" "$ALERT"
        else
            printf "."
        fi
    done

    # Check Cloudflare for recent 522 errors every 60 seconds
    CURRENT_MINUTE=$(date +%M)
    if [ "$((CURRENT_MINUTE % 1))" -eq 0 ]; then
        # Query Cloudflare API for errors in the last 5 minutes
        CF_ERRORS=$(curl -s -X POST 'https://api.cloudflare.com/client/v4/graphql' \
            -H 'X-Auth-Email: kevinmcaleer@gmail.com' \
            -H 'X-Auth-Key: e9c5d416693922a75616f2fc8460c02b159d8' \
            -H 'Content-Type: application/json' \
            --data "{\"query\":\"{ viewer { zones(filter: {zoneTag: \\\"e06ab6d949dd97494778641a47a50c6b\\\"}) { httpRequests1mGroups(limit: 5, filter: {datetime_gt: \\\"$(date -u -v-5M '+%Y-%m-%dT%H:%M:%SZ')\\\"}) { dimensions { datetime } sum { responseStatusMap { edgeResponseStatus requests } } } } } }\"}" \
            | jq -r '.data.viewer.zones[0].httpRequests1mGroups[]? | select(.sum.responseStatusMap[]? | select(.edgeResponseStatus >= 500)) | "\(.dimensions.datetime): \([.sum.responseStatusMap[] | select(.edgeResponseStatus >= 500) | "HTTP\(.edgeResponseStatus)=\(.requests)"] | join(", "))"' 2>/dev/null)

        if [ -n "$CF_ERRORS" ]; then
            echo ""
            echo "$TIMESTAMP - CLOUDFLARE ERRORS DETECTED:"
            echo "$CF_ERRORS" | while read line; do
                echo "  $line" | tee -a "$LOG_FILE"
            done
            echo ""
        fi
    fi

    sleep 10
done
