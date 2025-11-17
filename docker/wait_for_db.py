import os
import time
import pymysql

host = os.getenv("MYSQL_HOST", os.getenv("DB_HOST", "db"))
# Inside Docker, use port 3306 (internal). Port 3036 is only for external access
port = int(os.getenv("MYSQL_PORT", os.getenv("DB_PORT", "3306")))
user = os.getenv("MYSQL_USER", "root")
password = os.getenv("MYSQL_PASSWORD", "root")

def wait_for_db(timeout=120):
    """Wait for MySQL to be ready. Increased timeout for first-time setup."""
    start = time.time()
    max_attempts = timeout // 2
    attempt = 0
    
    while attempt < max_attempts:
        try:
            conn = pymysql.connect(
                host=host, 
                port=port, 
                user=user, 
                password=password,
                connect_timeout=5
            )
            conn.close()
            print(f"MySQL reachable at {host}:{port}")
            return True
        except Exception as e:
            attempt += 1
            elapsed = time.time() - start
            if elapsed > timeout:
                print(f"Timed out waiting for MySQL after {timeout}s: {e}")
                return False
            if attempt % 5 == 0:  # Print every 5 attempts
                print(f"Waiting for MySQL at {host}:{port}... (attempt {attempt}/{max_attempts})")
            time.sleep(2)
    
    print(f"Failed to connect to MySQL after {max_attempts} attempts")
    return False

if __name__ == '__main__':
    ok = wait_for_db()
    if not ok:
        raise SystemExit(1)
