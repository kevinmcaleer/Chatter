#!/bin/bash
# Quick deployment script - Run this from your local machine
# It will guide you through the fix process

echo "========================================="
echo "Database Server Fix - Deployment Guide"
echo "========================================="
echo ""
echo "Step 1: Copy the fix script to the database server"
echo "Run this command and enter your password when prompted:"
echo ""
echo "scp /Users/kev/Python/Chatter/scripts/diagnosis/fix_pg_hba_correct.sh kev@192.168.2.3:/tmp/fix_pg_hba.sh"
echo ""
echo "----------------------------------------"
read -p "Press ENTER when script is copied..."
echo ""

echo "Step 2: SSH to the database server and run the fix"
echo "Run these commands:"
echo ""
echo "ssh kev@192.168.2.3"
echo "sudo bash /tmp/fix_pg_hba.sh"
echo ""
echo "----------------------------------------"
read -p "Press ENTER when fix is complete..."
echo ""

echo "Step 3: Test the connection from your local machine"
echo "Running test now..."
echo ""
python3 /Users/kev/Python/Chatter/test_db_connection.py

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================="
    echo "✓ SUCCESS! Database is now accessible"
    echo "========================================="
    echo ""
    echo "Next step: Restart Chatter applications on servers"
    echo "  ssh kev@192.168.2.2"
    echo "  docker-compose restart"
else
    echo ""
    echo "========================================="
    echo "✗ Connection still failing"
    echo "========================================="
    echo ""
    echo "Check the output from the fix script for errors"
    echo "Or review the manual guide at:"
    echo "  /Users/kev/Python/Chatter/scripts/diagnosis/MANUAL_DB_SERVER_FIX.md"
fi
