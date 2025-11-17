#!/bin/bash
# Startup script for running the AI agent only

set -e

echo "=========================================="
echo "Weather AI Agent"
echo "=========================================="

# Wait for database to be ready
echo "Waiting for MySQL database..."
python docker/wait_for_db.py

# Start the agent
echo "Starting weather agent..."
exec python -m scripts.run_agent "$@"

