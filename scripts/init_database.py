"""Initialize the database by creating tables and optionally populating with data."""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Create the database and table if they don't exist."""
    storage_type = os.getenv("STORAGE_TYPE", "bigquery").lower()
    
    if storage_type != "mysql":
        logger.info(f"STORAGE_TYPE is '{storage_type}', not 'mysql'. Skipping MySQL initialization.")
        return
    
    logger.info("Initializing MySQL database...")
    
    from ingestion.loader_sql import MySQLLoader
    
    loader = MySQLLoader()
    
    try:
        # This will create the database and all tables if they don't exist
        loader.ensure_table()
        logger.info("Database and tables created successfully!")
        
        # Check if cities table has data
        loader.connect()
        with loader.conn.cursor() as cur:
            cur.execute(f"USE `{loader.database}`")
            
            # Check cities
            cur.execute("SELECT COUNT(*) as count FROM cities")
            cities_result = cur.fetchone()
            cities_count = cities_result['count'] if cities_result else 0
            
            # Check weather observations
            if loader.use_improved_schema:
                cur.execute("SELECT COUNT(*) as count FROM weather_observations")
                obs_result = cur.fetchone()
                obs_count = obs_result['count'] if obs_result else 0
                table_name = "weather_observations"
            else:
                cur.execute(f"SELECT COUNT(*) as count FROM `{loader.table}`")
                obs_result = cur.fetchone()
                obs_count = obs_result['count'] if obs_result else 0
                table_name = loader.table
            
            logger.info(f"Cities table: {cities_count} cities")
            logger.info(f"Weather observations table: {obs_count} rows")
            
            if cities_count == 0:
                logger.info("Cities table is empty. To populate it, run:")
                logger.info("  python scripts/populate_cities.py")
            
            if obs_count == 0:
                logger.info(f"Weather observations table is empty. To populate with data, run:")
                logger.info("  python -m scripts.one_shot")
                logger.info("Or:")
                logger.info("  docker-compose exec app python -m scripts.one_shot")
                
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


if __name__ == "__main__":
    try:
        init_database()
        print("\n[SUCCESS] Database initialized!")
    except Exception as e:
        print(f"\n[ERROR] Failed to initialize database: {e}")
        sys.exit(1)

