# Quick Start Guide

## Single Command Deployment

### Prerequisites
- Docker and Docker Compose installed
- OpenWeatherMap API key (free tier: https://openweathermap.org/api)
- OpenAI API key (https://platform.openai.com/api-keys)

### Steps

1. **Create `.env` file:**
```bash
OPENWEATHER_API_KEY=your_openweathermap_key_here
OPENAI_API_KEY=your_openai_key_here
STORAGE_TYPE=mysql
MYSQL_HOST=db
MYSQL_PORT=3036
MYSQL_USER=root
MYSQL_PASSWORD=root
MYSQL_DB=weather_db
MYSQL_TABLE=weather_data
BACKFILL_DAYS=60
LOG_LEVEL=INFO
```

2. **Start everything:**
```bash
docker-compose up --build
```

3. **Wait for initialization** (first run takes 10-20 minutes for backfill)

4. **Use the agent:**
```bash
# Interactive mode
docker-compose exec agent python -m scripts.run_agent

# Single query
docker-compose exec agent python -m scripts.run_agent "What is the weather in Colombo?"
```

## What's Running

- **MySQL Database**: Port 3036
- **Orchestrator Service**: Fetches data, backfills, runs hourly updates
- **AI Agent Service**: Interactive weather assistant

## Verify Installation

```bash
# Check data in database
docker-compose exec db mysql -uroot -proot -e "SELECT COUNT(*) FROM weather_db.weather_data;"

# Check logs
docker-compose logs -f

# Test agent
docker-compose exec agent python -m scripts.run_agent "What is the current weather in London?"
```

## Stop Services

```bash
docker-compose down
```


