import os
import logging
from typing import Dict, List
from datetime import datetime, timezone
import pymysql

logger = logging.getLogger(__name__)


class MySQLLoader:
    """Simple MySQL loader with idempotent upsert using PRIMARY KEY (city, timestamp).

    Reads connection info from env vars if not provided:
      MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, MYSQL_TABLE
    """

    def __init__(self,
                 host: str = None,
                 port: int = None,
                 user: str = None,
                 password: str = None,
                 database: str = None,
                 table: str = None):
        self.host = host or os.getenv("MYSQL_HOST", "127.0.0.1")
        self.port = int(port or os.getenv("MYSQL_PORT", "3306"))
        self.user = user or os.getenv("MYSQL_USER", "root")
        self.password = password or os.getenv("MYSQL_PASSWORD", "")
        self.database = database or os.getenv("MYSQL_DB", "weather_db")
        self.table = table or os.getenv("MYSQL_TABLE", "weather_data")

        self.conn = None

    def connect(self):
        if self.conn and self.conn.open:
            return
        logger.info("Connecting to MySQL %s:%s db=%s user=%s", self.host, self.port, self.database, self.user)
        self.conn = pymysql.connect(host=self.host,
                                    port=self.port,
                                    user=self.user,
                                    password=self.password,
                                    autocommit=True,
                                    cursorclass=pymysql.cursors.DictCursor)

    def ensure_table(self):
        """Create database and table if missing."""
        self.connect()
        with self.conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{self.database}`")
            cur.execute(f"USE `{self.database}`")

            # Table schema mirrors BigQuery schema types as reasonable MySQL types.
            create_sql = f"""
            CREATE TABLE IF NOT EXISTS `{self.table}` (
              city VARCHAR(255) NOT NULL,
              `timestamp` DATETIME NOT NULL,
              temperature DOUBLE,
              feels_like DOUBLE,
              pressure INT,
              humidity INT,
              wind_speed DOUBLE,
              wind_deg INT,
              `condition` VARCHAR(255),
              `raw` JSON,
              updated_at DATETIME,
              PRIMARY KEY (city, `timestamp`)
            ) ENGINE=InnoDB;
            """
            cur.execute(create_sql)
        logger.info("Ensured MySQL table %s.%s exists", self.database, self.table)

    def row_to_sql(self, normalized: Dict) -> Dict:
        ts = normalized.get("timestamp")
        # Accept ISO strings or numeric epoch seconds
        if isinstance(ts, (int, float)):
            ts_val = datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        else:
            # attempt to parse ISO-like strings by slicing
            ts_val = ts

        return {
            "city": normalized.get("city"),
            "timestamp": ts_val,
            "temperature": normalized.get("temperature"),
            "feels_like": normalized.get("feels_like"),
            "pressure": normalized.get("pressure"),
            "humidity": normalized.get("humidity"),
            "wind_speed": normalized.get("wind_speed"),
            "wind_deg": normalized.get("wind_deg"),
            "condition": normalized.get("condition"),
            "raw": normalized.get("raw") or {},
            "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        }

    def insert_rows(self, rows: List[Dict]):
        if not rows:
            return
        self.connect()
        with self.conn.cursor() as cur:
            cur.execute(f"USE `{self.database}`")
            insert_sql = f"""
            INSERT INTO `{self.table}`
              (city, `timestamp`, temperature, feels_like, pressure, humidity, wind_speed, wind_deg, `condition`, `raw`, updated_at)
            VALUES
              (%(city)s, %(timestamp)s, %(temperature)s, %(feels_like)s, %(pressure)s, %(humidity)s, %(wind_speed)s, %(wind_deg)s, %(condition)s, %(raw)s, %(updated_at)s)
            ON DUPLICATE KEY UPDATE
              temperature=VALUES(temperature), feels_like=VALUES(feels_like), pressure=VALUES(pressure), humidity=VALUES(humidity),
              wind_speed=VALUES(wind_speed), wind_deg=VALUES(wind_deg), `condition`=VALUES(`condition`), raw=VALUES(raw), updated_at=VALUES(updated_at)
            """
            # If rows are normalized dicts (from transformer), convert via row_to_sql
            prepared = []
            for r in rows:
                # If this looks like an already-prepared SQL row (has updated_at), use as-is
                if isinstance(r, dict) and 'updated_at' in r and 'timestamp' in r:
                    rr = r.copy()
                else:
                    rr = self.row_to_sql(r)

                # Ensure raw is dumped as JSON string if dict
                raw = rr.get("raw")
                if isinstance(raw, (dict, list)):
                    import json
                    rr["raw"] = json.dumps(raw, default=str)
                else:
                    rr["raw"] = str(raw or "{}")

                prepared.append(rr)

            cur.executemany(insert_sql, prepared)
        logger.info("Inserted/updated %d rows into %s.%s", len(rows), self.database, self.table)

    def get_latest_weather(self, city: str) -> Dict:
        self.connect()
        with self.conn.cursor() as cur:
            cur.execute(f"USE `{self.database}`")
            cur.execute(f"SELECT * FROM `{self.table}` WHERE city=%s ORDER BY `timestamp` DESC LIMIT 1", (city,))
            row = cur.fetchone()
            return row or {}

    def get_weather_history(self, city: str, days: int = 7) -> List[Dict]:
        self.connect()
        with self.conn.cursor() as cur:
            cur.execute(f"USE `{self.database}`")
            cur.execute(f"SELECT * FROM `{self.table}` WHERE city=%s AND `timestamp` >= NOW() - INTERVAL %s DAY ORDER BY `timestamp` DESC", (city, int(days)))
            return cur.fetchall()
