"""Storage abstraction exposing retrieval helpers.

Provides:
  - get_latest_weather(city: str) -> dict
  - get_weather_history(city: str, days: int) -> list[dict]

Automatically picks the loader implementation based on the env var
`STORAGE_TYPE` ("bigquery" or "mysql").
"""
import os
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

STORAGE = os.getenv("STORAGE_TYPE", "bigquery").lower()

if STORAGE == "mysql":
    from ingestion.loader_sql import MySQLLoader as Loader
else:
    from ingestion.loader_bigquery import BigQueryLoader as Loader

# instantiate a single loader for convenience
_loader = Loader()

def get_latest_weather(city: str) -> Dict:
    """Return the most recent weather row for `city` or an empty dict.

    The returned dict structure matches the underlying loader's output:
    - BigQuery: keys are column names (city, timestamp, temperature, ...)
    - MySQL: same keys produced by the SQL loader
    """
    try:
        return _loader.get_latest_weather(city)
    except Exception as e:
        logger.exception("Failed to fetch latest weather for %s: %s", city, e)
        return {}


def get_weather_history(city: str, days: int = 7) -> List[Dict]:
    """Return weather history for `city` in the last `days` days (newest-first).

    The loader will return a list of dicts; the exact column names are the same
    as used when inserting (city, timestamp, temperature, ...).
    """
    try:
        return _loader.get_weather_history(city, days=days)
    except Exception as e:
        logger.exception("Failed to fetch weather history for %s: %s", city, e)
        return []


if __name__ == "__main__":
    # quick manual test
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("city", nargs="?", default="London")
    p.add_argument("--days", type=int, default=7)
    args = p.parse_args()

    print("Latest:", get_latest_weather(args.city))
    hist = get_weather_history(args.city, days=args.days)
    print(f"History ({len(hist)} rows):")
    for r in hist[:5]:
        print(r)
