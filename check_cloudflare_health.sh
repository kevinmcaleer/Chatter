#!/bin/bash

# Check Cloudflare health check logs and status
# This script queries Cloudflare API for health monitor status

ZONE_ID="e9b5acf1adfb8108c7ef573b634fd94f"  # kevsrobots.com zone

echo "=== Cloudflare Health Check Status ==="
echo "Checking health monitors for kevsrobots.com..."
echo ""

# Check if CF_API_TOKEN is set
if [ -z "$CF_API_TOKEN" ]; then
    echo "ERROR: CF_API_TOKEN environment variable not set"
    echo "Please set it with: export CF_API_TOKEN='your-token'"
    exit 1
fi

# Get all health checks for the zone
echo "Fetching health monitors..."
curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/healthchecks" \
    -H "Authorization: Bearer $CF_API_TOKEN" \
    -H "Content-Type: application/json" | jq '.'

echo ""
echo "=== Recent Analytics (last 24 hours) ==="
# Get zone analytics for the last 24 hours
curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/analytics/dashboard?since=-1440" \
    -H "Authorization: Bearer $CF_API_TOKEN" \
    -H "Content-Type: application/json" | jq '.result.timeseries[] | select(.requests.all > 0) | {time: .since, requests: .requests.all, cached: .requests.cached, uncached: .requests.uncached}'

echo ""
echo "=== Checking nginx access logs on load balancer ==="
echo "SSH to 192.168.1.4 and check /health endpoint requests..."
echo ""
echo "Run this command manually:"
echo "ssh 192.168.1.4 'docker exec nginx tail -1000 /var/log/nginx/access.log | grep \"/health\"'"
