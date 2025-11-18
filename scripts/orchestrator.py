# scripts/orchestrator.py
import os
from dotenv import load_dotenv
from ingestion.weather_client import WeatherClient
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta, timezone
import time
import logging
import json
import os

load_dotenv()
logging.basicConfig(level=logging.INFO)

STORAGE = os.getenv("STORAGE_TYPE", "bigquery").lower()

# choose storage loader implementation
if STORAGE == "mysql" or STORAGE == "mariadb":
    from ingestion.loader_sql import MySQLLoader as StorageLoader
else:
    from ingestion.loader_bigquery import BigQueryLoader as StorageLoader

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
bq_loader = StorageLoader()
bq_loader.ensure_table()
weather_client = WeatherClient(API_KEY)

# --- Core function to fetch & insert weather ---
def fetch_and_store_weather(simulated_timestamp=None):
    """
    Fetch current weather (or simulated historical weather) and store in database.
    Includes job logging for monitoring.
    """
    import uuid
    from datetime import datetime, timezone
    
    job_id = f"ingest_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    job_type = "backfill" if simulated_timestamp else "scheduled"
    started_at = datetime.now(timezone.utc)
    
    try:
        # Log job start
        if hasattr(bq_loader, 'log_ingestion_job'):
            bq_loader.log_ingestion_job(
                job_id=job_id,
                job_type=job_type,
                status="running",
                started_at=started_at,
                cities_processed=len(CITIES)
            )
        
        raw_data = weather_client.fetch_multiple_cities(CITIES)
        normalized = [weather_client.normalize_weather(d) for d in raw_data]

        # Adjust timestamp for backfill (normalizer uses ISO timestamps)
        for rec in normalized:
            if simulated_timestamp:
                rec["timestamp"] = simulated_timestamp.isoformat()

        # Convert to loader-specific rows and insert (idempotent by design)
        if hasattr(bq_loader, 'row_to_bq'):
            rows = [bq_loader.row_to_bq(r) for r in normalized]
        else:
            rows = normalized
        
        # Insert with job tracking
        if hasattr(bq_loader, 'insert_rows'):
            bq_loader.insert_rows(rows, job_id=job_id)
        else:
            bq_loader.insert_rows(rows)

        completed_at = datetime.now(timezone.utc)
        records_inserted = len(rows)
        
        # Log job completion
        if hasattr(bq_loader, 'log_ingestion_job'):
            bq_loader.log_ingestion_job(
                job_id=job_id,
                job_type=job_type,
                status="completed",
                started_at=started_at,
                completed_at=completed_at,
                cities_processed=len(CITIES),
                records_inserted=records_inserted,
                records_updated=records_inserted  # ON DUPLICATE KEY UPDATE counts as updates
            )

        logging.info("Weather ingestion completed for timestamp: %s (job_id: %s)",
                     simulated_timestamp.isoformat() if simulated_timestamp else "current", job_id)
    
    except Exception as e:
        completed_at = datetime.now(timezone.utc)
        error_msg = str(e)
        
        # Log job failure
        if hasattr(bq_loader, 'log_ingestion_job'):
            bq_loader.log_ingestion_job(
                job_id=job_id,
                job_type=job_type,
                status="failed",
                started_at=started_at,
                completed_at=completed_at,
                cities_processed=len(CITIES),
                error_message=error_msg
            )
        
        logging.error("Weather ingestion failed (job_id: %s): %s", job_id, error_msg)
        raise

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
