# Weather Intelligence Platform

End-to-end Python system that ingests weather data for 100+ cities, stores it with an idempotent MySQL pipeline, exposes REST retrieval APIs, and layers an OpenAI-powered agent on top of the same data. Everything runs locally or in Docker with a single command.

---

## Highlights

- **Ingestion & orchestration** – APScheduler jobs fetch OpenWeatherMap data, backfill ~60 days on startup, and push rows through a staging→merge workflow with ingestion job logging.
- **Storage & retrieval** – Improved MySQL schema (`cities`, `weather_observations`, `ingestion_logs`) plus shared helpers (`get_latest_weather`, `get_weather_history`) that power the API, scripts, and agent.
- **AI agentic workflow** – OpenAI function calling with three tools (current weather, history, temperature stats), guardrails, and automatic fallback to live API data when the DB is empty.
- **Turnkey deployment** – Docker Compose spins up MySQL, orchestrator, FastAPI service, and agent. Local dev mirrors the same `.env` driven config.

## Architecture Overview

- **Ingestion layer (`ingestion/`)**
  - `weather_client.py`: OpenWeatherMap wrapper.
  - `transformer.py`: canonical normalization.
  - `loader_sql.py`: MySQL connector, schema bootstrapper, staging/merge logic, ingestion logging.
  - `store.py`: selects the loader (MySQL by default) and exposes retrieval helpers.

- **Pipelines & tooling (`scripts/`)**
  - `orchestrator.py`: startup backfill + hourly scheduler.
  - `run_pipeline.py` / `one_shot.py`: manual ingest helpers.
  - Utilities: `init_database.py`, `populate_cities.py`, `view_ingestion_logs.py`, `check_mysql.py`, `run_agent.py`, etc.

- **API layer (`api/`)**
  - FastAPI service (`api/main.py`) exposing `/health`, `/api/weather/latest`, `/api/weather/history`, `/api/agent/query`.
  - Token-based auth via `verify_bearer_token`.
  - Shared WeatherAgent singleton in `api/services.py`.

- **Agent layer (`agent/`)**
  - `weather_agent.py`: OpenAI client, guardrails, tool wiring, fallback logic.
  - `weather_tools.py`: connects agent tool calls to the retrieval helpers.

---

## Project Requirements Checklist

### Data Collection & Orchestration 
- Fetches weather for 100+ curated cities.
- APScheduler hourly jobs plus configurable 60-day backfill.
- Idempotent upsert keyed by `(city, timestamp)` with staging table deduplication.
- Ingestion job metadata persisted in `ingestion_logs`.

### Storage & Retrieval 
- Improved normalized schema (see `docs/DATABASE_SCHEMA.md`).
- Retrieval helpers (`get_latest_weather`, `get_weather_history`) consumed by API and agent.
- Helper scripts for schema creation, city seeding, and log inspection.

### AI Agentic Workflow 
- OpenAI Agents SDK with three custom tools.
- Safety guardrails (keyword filter + LLM classifier + polite refusal).
- Automatic fallback to live OpenWeatherMap data when MySQL misses.

### Deployment & Delivery 
- Docker Compose brings up DB, orchestrator, API, and agent with `docker-compose up --build`.
- `.env.example` documents all secrets/config.
- Testable with `python -m pytest -q`.

---

## Getting Started

- **Hands-on quick start**: see [`QUICK_START.md`](QUICK_START.md) for environment setup, Docker commands, local dev instructions, and curl snippets.
- **Sample outputs**: review [`example_queries_and_responses.md`](example_queries_and_responses.md) for real responses you can reproduce.
- **Local dev without Docker**: follow the “Local Setup” section in `QUICK_START.md` (pip install, `.env`, `uvicorn`, etc.).

---

## Development Tips

- Install dependencies: `pip install -r requirements.txt`.
- Copy `.env.example` → `.env` and set `OPENWEATHER_API_KEY`, `OPENAI_API_KEY`, `API_AUTH_TOKEN`, and MySQL creds.
- Run tests: `python -m pytest -q`.
- Start the API locally: `uvicorn api.main:app --reload --host 0.0.0.0 --port 8000` (remember to export `API_AUTH_TOKEN`).
- Inspect data quickly: `python -c "from ingestion.store import get_latest_weather; print(get_latest_weather('London'))"`.

---

## Troubleshooting Highlights

- **MySQL connection errors**: `python scripts/check_mysql.py`; ensure `.env` has `MYSQL_HOST`, `MYSQL_PORT=3036`, `MYSQL_USER=root`, `MYSQL_PASSWORD=root`.
- **Tables missing**: `python scripts/init_database.py` then `python -m scripts.one_shot`.
- **Need ingestion status**: `python scripts/view_ingestion_logs.py --limit 20` (or `--status failed`).
- **Agent not responding**: confirm `OPENAI_API_KEY` is set and try `python -m scripts.run_agent "What is the weather in Colombo?"`.

---

## Roadmap Ideas

- Enable the BigQuery storage path (set `STORAGE_TYPE=bigquery` once GCP credentials are configured).
- Add observability (Prometheus metrics, alerts from `ingestion_logs`).
- Extend agent tools or prompts for additional analytics queries.

---