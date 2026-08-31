#!/usr/bin/env bash

# Facebook Messenger 24/7 Persistent Server Startup Script
echo "========================================================="
echo "   ⚡ FB MESSENGER 24/7 NON-STOP BOT SERVER STARTUP    "
echo "========================================================="

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Check if venv exists, if not create it
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install / update requirements
echo "📦 Checking and installing dependencies..."
pip install -r requirements.txt --quiet

# Launch 24/7 Supervisor
echo "🛡️ Starting 24/7 Supervisor Watchdog..."
echo "🌐 Dashboard Web URL: http://127.0.0.1:8080"
echo "========================================================="
python3 supervisor.py
