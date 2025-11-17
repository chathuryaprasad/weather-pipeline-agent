FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy project
COPY . /app

# Make startup scripts executable
RUN chmod +x docker/startup.sh docker/startup_agent.sh || true

ENV PYTHONUNBUFFERED=1

# Default command: start orchestrator (scheduler). Can be overridden with docker-compose command.
CMD ["python", "-m", "scripts.orchestrator"]
