# scripts/orchestrator.py
import os
from dotenv import load_dotenv
from ingestion.loader_bigquery import BigQueryLoader
from ingestion.weather_client import WeatherClient
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta, timezone
import time
import logging
import json
import os

load_dotenv()
logging.basicConfig(level=logging.INFO)

# --- Configuration ---
API_KEY = os.getenv("OPENWEATHER_API_KEY")
# Load the curated city list from config; fallback to a small set
try:
    with open(os.path.join(os.path.dirname(__file__), "..", "config", "cities_list.json"), "r", encoding="utf-8") as f:
        CITIES = json.load(f)
except Exception:
    CITIES = [
        "Colombo", "Galle", "Kandy", "Jaffna", "Matara",
        "Anuradhapura", "Trincomalee", "Hambantota", "Negombo", "Ratnapura"
    ]

# --- Initialize clients ---
bq_loader = BigQueryLoader()
bq_loader.ensure_table()
weather_client = WeatherClient(API_KEY)

# --- Core function to fetch & insert weather ---
def fetch_and_store_weather(simulated_timestamp=None):
    """
    Fetch current weather (or simulated historical weather) and store in BigQuery.
    """
    raw_data = weather_client.fetch_multiple_cities(CITIES)
    normalized = [weather_client.normalize_weather(d) for d in raw_data]

    # Adjust timestamp for backfill (normalizer uses ISO timestamps)
    for rec in normalized:
        if simulated_timestamp:
            rec["timestamp"] = simulated_timestamp.isoformat()

    # Convert to BigQuery rows and insert (idempotent via insert_ids)
    rows = [bq_loader.row_to_bq(r) for r in normalized]
    bq_loader.insert_rows(rows)

    logging.info("Weather ingestion completed for timestamp: %s",
                 simulated_timestamp.isoformat() if simulated_timestamp else "current")

# --- Backfill function ---
def backfill_weather(days=60):
    """
    Backfill past `days` of weather data at startup.
    """
    logging.info("Starting backfill for last %d days...", days)
    for i in range(days, 0, -1):
        ts = datetime.now(timezone.utc) - timedelta(days=i)
        fetch_and_store_weather(simulated_timestamp=ts)
    logging.info("Backfill completed!")

# --- Scheduler for hourly updates ---
def start_scheduler():
    """
    Schedule hourly updates for new data.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_and_store_weather, 'interval', hours=1)
    scheduler.start()
    logging.info("Scheduler started: weather updates every hour.")

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logging.info("Scheduler stopped.")

# --- Main orchestrator ---
if __name__ == "__main__":
    # Default to a 60-day backfill at startup unless overridden.
    days = int(os.getenv("BACKFILL_DAYS", "60"))
    if days > 0:
        bq_loader.ensure_table()
        # NOTE: OpenWeatherMap historical full-month data requires a paid plan.
        # This backfill will fetch current observations and attach historical timestamps
        # to provide a filled time-series. For true historical observations consider
        # using OWM One Call Historical (paid) or a third-party dataset.
        backfill_weather(days=days)
    else:
        logging.info("Skipping backfill (BACKFILL_DAYS=%d)", days)

    start_scheduler()  # Step 2: start hourly updates
