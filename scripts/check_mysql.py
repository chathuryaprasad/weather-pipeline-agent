"""Check MySQL connection and provide setup instructions."""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

def check_mysql_connection():
    """Check if MySQL is accessible and provide setup instructions."""
    print("=" * 60)
    print("MySQL Connection Check")
    print("=" * 60)
    
    # Get connection settings
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    database = os.getenv("MYSQL_DB", "weather_db")
    storage_type = os.getenv("STORAGE_TYPE", "bigquery").lower()
    
    print(f"\nCurrent Settings:")
    print(f"  STORAGE_TYPE: {storage_type}")
    print(f"  MYSQL_HOST: {host}")
    print(f"  MYSQL_PORT: {port}")
    print(f"  MYSQL_USER: {user}")
    print(f"  MYSQL_DB: {database}")
    
    if storage_type != "mysql":
        print(f"\n[INFO] STORAGE_TYPE is set to '{storage_type}', not 'mysql'")
        print("If you want to use MySQL, set STORAGE_TYPE=mysql in your .env file")
        return
    
    print("\n" + "-" * 60)
    print("Testing MySQL Connection...")
    print("-" * 60)
    
    try:
        import pymysql
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            connect_timeout=5
        )
        conn.close()
        print("[SUCCESS] MySQL connection successful!")
        
        # Check if database exists
        try:
            conn = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                connect_timeout=5
            )
            with conn.cursor() as cur:
                cur.execute("SHOW TABLES")
                tables = cur.fetchall()
                print(f"[SUCCESS] Database '{database}' exists with {len(tables)} table(s)")
            conn.close()
        except Exception as e:
            print(f"[WARNING] Database '{database}' may not exist: {e}")
            
    except ImportError:
        print("[ERROR] pymysql is not installed. Run: pip install PyMySQL")
    except Exception as e:
        error_str = str(e)
        print(f"[ERROR] Cannot connect to MySQL: {error_str}")
        
        if "refused" in error_str.lower() or "10061" in error_str:
            print("\n" + "=" * 60)
            print("MySQL is not running. To start it:")
            print("=" * 60)
            print("\nOption 1: Start with Docker Compose")
            print("  docker-compose up -d db")
            print("\nOption 2: Check if Docker is running")
            print("  docker ps")
            print("\nOption 3: If using Docker, make sure your .env has:")
            print("  STORAGE_TYPE=mysql")
            print("  MYSQL_HOST=127.0.0.1")
            print("  MYSQL_PORT=3036")
            print("  MYSQL_USER=root")
            print("  MYSQL_PASSWORD=root")
            print("  MYSQL_DB=weather_db")
        elif "access denied" in error_str.lower() or "1045" in error_str:
            print("\n[ERROR] Authentication failed. Check MYSQL_USER and MYSQL_PASSWORD in .env")
        else:
            print(f"\n[ERROR] Connection error: {e}")


if __name__ == "__main__":
    check_mysql_connection()

