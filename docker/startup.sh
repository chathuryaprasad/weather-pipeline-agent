#!/bin/bash
# Comprehensive startup script for the weather data pipeline and AI agent

set -e

echo "=========================================="
echo "Weather Data Pipeline & AI Agent Startup"
echo "=========================================="

# Wait for database to be ready
echo "Waiting for MySQL database..."
python docker/wait_for_db.py

# Initialize database (create tables if needed)
echo "Initializing database..."
python scripts/init_database.py

# Run initial data fetch
echo "Fetching initial weather data..."
python -m scripts.one_shot

# Start orchestrator (handles backfill and hourly updates)
echo "Starting orchestrator (backfill + hourly scheduler)..."
exec python -m scripts.orchestrator

