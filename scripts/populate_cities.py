"""Populate cities table with metadata from weather data."""
import sys
import os
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def populate_cities():
    """Populate cities table from cities_list.json and weather data."""
    storage_type = os.getenv("STORAGE_TYPE", "bigquery").lower()
    
    if storage_type != "mysql":
        logger.info(f"STORAGE_TYPE is '{storage_type}', not 'mysql'. Skipping cities population.")
        return
    
    from ingestion.loader_sql import MySQLLoader
    from ingestion.weather_client import WeatherClient
    
    loader = MySQLLoader()
    # Ensure all tables exist (including cities table)
    loader.ensure_table()
    
    if not loader.use_improved_schema:
        logger.warning("Improved schema is disabled. Cities table will not be populated.")
        return
    
    # Load city list
    cities_file = project_root / "config" / "cities_list.json"
    try:
        with open(cities_file, 'r', encoding='utf-8') as f:
            city_names = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load cities list: {e}")
        return
    
    logger.info(f"Populating cities table with {len(city_names)} cities...")
    
    # Get API key for fetching city metadata
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        logger.warning("OPENWEATHER_API_KEY not set. Populating cities without metadata.")
        weather_client = None
    else:
        weather_client = WeatherClient(api_key)
    
    populated = 0
    import time
    
    for idx, city_name in enumerate(city_names, 1):
        try:
            # Try to get city metadata from weather API
            if weather_client:
                try:
                    weather_data = weather_client.fetch_city_weather(city_name)
                    if weather_data:
                        sys_data = weather_data.get("sys", {})
                        coord = weather_data.get("coord", {})
                        
                        city_id = loader.upsert_city(
                            city_name=city_name,
                            country=sys_data.get("country"),
                            country_code=sys_data.get("country"),
                            latitude=coord.get("lat"),
                            longitude=coord.get("lon")
                        )
                        if city_id:
                            populated += 1
                            if populated % 10 == 0:
                                logger.info(f"Populated {populated}/{len(city_names)} cities...")
                        # Small delay to avoid rate limits
                        if idx < len(city_names):
                            time.sleep(0.1)
                        continue
                except Exception as e:
                    logger.debug(f"Could not fetch metadata for {city_name}: {e}")
            
            # Fallback: insert city without metadata
            city_id = loader.upsert_city(city_name=city_name)
            if city_id:
                populated += 1
                
        except Exception as e:
            logger.warning(f"Failed to populate city {city_name}: {e}")
    
    logger.info(f"Successfully populated {populated}/{len(city_names)} cities in the database.")


if __name__ == "__main__":
    try:
        populate_cities()
        print("\n[SUCCESS] Cities table populated!")
    except Exception as e:
        logger.exception(f"Error populating cities: {e}")
        print(f"\n[ERROR] Failed to populate cities: {e}")
        sys.exit(1)

