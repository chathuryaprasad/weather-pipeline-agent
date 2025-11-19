#!/bin/bash
# Startup script for the FastAPI service

set -e

echo "=========================================="
echo "Weather API"
echo "=========================================="

echo "Waiting for MySQL database..."
python docker/wait_for_db.py

echo "Starting FastAPI server..."
exec uvicorn api.main:app --host 0.0.0.0 --port 8000

