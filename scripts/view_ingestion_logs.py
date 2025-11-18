"""View ingestion logs for monitoring and debugging."""
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def view_logs(limit: int = 20, status: str = None):
    """View ingestion logs."""
    storage_type = os.getenv("STORAGE_TYPE", "bigquery").lower()
    
    if storage_type != "mysql":
        logger.info(f"STORAGE_TYPE is '{storage_type}', not 'mysql'. Ingestion logs only available for MySQL.")
        return
    
    from ingestion.loader_sql import MySQLLoader
    
    loader = MySQLLoader()
    
    if not loader.use_improved_schema:
        logger.warning("Improved schema is disabled. Ingestion logs not available.")
        return
    
    loader.connect()
    with loader.conn.cursor() as cur:
        cur.execute(f"USE `{loader.database}`")
        
        query = "SELECT * FROM ingestion_logs"
        params = []
        
        if status:
            query += " WHERE status = %s"
            params.append(status)
        
        query += " ORDER BY started_at DESC LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        logs = cur.fetchall()
        
        if not logs:
            print("No ingestion logs found.")
            return
        
        print(f"\n{'='*100}")
        print(f"Ingestion Logs (showing {len(logs)} most recent)")
        print(f"{'='*100}\n")
        
        for log in logs:
            duration = f"{log['duration_seconds']}s" if log['duration_seconds'] else "N/A"
            print(f"Job ID: {log['job_id']}")
            print(f"  Type: {log['job_type']} | Status: {log['status']}")
            print(f"  Started: {log['started_at']} | Completed: {log['completed_at'] or 'N/A'} | Duration: {duration}")
            print(f"  Cities: {log['cities_processed']} | Inserted: {log['records_inserted']} | Updated: {log['records_updated']} | Failed: {log['records_failed']}")
            if log['error_message']:
                print(f"  Error: {log['error_message']}")
            print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="View ingestion logs")
    parser.add_argument("--limit", type=int, default=20, help="Number of logs to show")
    parser.add_argument("--status", choices=["running", "completed", "failed"], help="Filter by status")
    args = parser.parse_args()
    
    try:
        view_logs(limit=args.limit, status=args.status)
    except Exception as e:
        logger.exception(f"Error viewing logs: {e}")
        sys.exit(1)



