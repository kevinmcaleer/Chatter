#!/bin/bash
# Setup Cloudflare Tunnel on 192.168.2.3
# Run this script locally, it will SSH and execute commands

set -e

echo "Setting up Cloudflare Tunnel on dev03 (192.168.2.3)..."
echo ""

ssh kev@192.168.2.3 << 'ENDSSH'
set -e

echo "1. Installing cloudflared..."
cd /tmp
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb
sudo dpkg -i cloudflared-linux-arm64.deb
cloudflared --version

echo ""
echo "2. Creating credentials directory..."
sudo mkdir -p /etc/cloudflared

echo ""
echo "3. Creating credentials file..."
sudo tee /etc/cloudflared/49b119be-4908-4292-a174-d60d0fa8a8d6.json > /dev/null << 'EOF'
{"AccountTag":"88457c580f7c4c0b6d82a611759acc3b","TunnelSecret":"Rl5D1TjXVsITN4pRJje9tkqF0XJAfBcq3bbgSwijt/c=","TunnelID":"49b119be-4908-4292-a174-d60d0fa8a8d6","Endpoint":""}
EOF

sudo chmod 600 /etc/cloudflared/49b119be-4908-4292-a174-d60d0fa8a8d6.json
echo "✓ Credentials file created"

echo ""
echo "4. Creating tunnel configuration..."
sudo tee /etc/cloudflared/config.yml > /dev/null << 'EOF'
tunnel: 49b119be-4908-4292-a174-d60d0fa8a8d6
credentials-file: /etc/cloudflared/49b119be-4908-4292-a174-d60d0fa8a8d6.json

ingress:
  - hostname: chatter.kevsrobots.com
    service: http://192.168.2.2:8006
  - service: http_status:404
EOF
echo "✓ Config file created"

echo ""
echo "5. Installing cloudflared as a service..."
sudo cloudflared service install

echo ""
echo "6. Starting cloudflared service..."
sudo systemctl start cloudflared
sudo systemctl enable cloudflared

echo ""
echo "7. Checking service status..."
sudo systemctl status cloudflared --no-pager

echo ""
echo "========================================="
echo "✓ Cloudflare Tunnel setup complete!"
echo "========================================="
ENDSSH

echo ""
echo "Done! Check https://chatter.kevsrobots.com/docs in a minute"
