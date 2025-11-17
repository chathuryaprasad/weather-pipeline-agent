# scripts/run_pipeline.py
import os
from dotenv import load_dotenv
from ingestion.weather_client import WeatherClient
from datetime import datetime, timedelta, timezone
import logging
import json
import os

load_dotenv()
logging.basicConfig(level=logging.INFO)

API_KEY = os.getenv("OPENWEATHER_API_KEY")
STORAGE = os.getenv("STORAGE_TYPE", "bigquery").lower()

# Choose loader implementation depending on STORAGE_TYPE env var
if STORAGE == "mysql" or STORAGE == "mariadb":
    from ingestion.loader_sql import MySQLLoader as StorageLoader
else:
    from ingestion.loader_bigquery import BigQueryLoader as StorageLoader
# try to load the curated city list
try:
    with open(os.path.join(os.path.dirname(__file__), "..", "config", "cities_list.json"), "r", encoding="utf-8") as f:
        CITIES = json.load(f)
except Exception:
    CITIES = [
        "Colombo", "Galle", "Kandy", "Jaffna", "Matara",
        "Anuradhapura", "Trincomalee", "Hambantota", "Negombo", "Ratnapura"
    ]

bq_loader = StorageLoader()
weather_client = WeatherClient(API_KEY)

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

    # Convert to the loader-specific row shape. BigQueryLoader provides
    # row_to_bq, MySQLLoader expects a dict with canonical keys, so call
    # row_to_bq when available; otherwise send normalized dicts.
    rows_to_insert = []
    if hasattr(bq_loader, 'row_to_bq'):
        rows_to_insert = [bq_loader.row_to_bq(r) for r in normalized]
    else:
        rows_to_insert = normalized

    bq_loader.insert_rows(rows_to_insert)
    logging.info("Weather ingestion completed for timestamp: %s",
                 simulated_timestamp.isoformat() if simulated_timestamp else "current")
