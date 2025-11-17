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
        # This will create the database and table if they don't exist
        loader.ensure_table()
        logger.info("Database and table created successfully!")
        
        # Check if table has data
        loader.connect()
        with loader.conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) as count FROM `{loader.database}`.`{loader.table}`")
            result = cur.fetchone()
            count = result['count'] if result else 0
            
            if count == 0:
                logger.info(f"Table '{loader.table}' exists but is empty ({count} rows).")
                logger.info("To populate with data, run:")
                logger.info("  python -m scripts.run_pipeline")
                logger.info("Or:")
                logger.info("  docker-compose exec app python -m scripts.run_pipeline")
            else:
                logger.info(f"Table '{loader.table}' has {count} rows of data.")
                
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

