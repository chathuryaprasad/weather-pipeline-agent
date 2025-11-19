import os
import logging
import json
import uuid
from typing import Dict, List, Optional
from datetime import datetime, timezone
import pymysql
from ingestion.schema import get_all_schema_sql

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
        # Use new table name by default, but allow override for backward compatibility
        self.table = table or os.getenv("MYSQL_TABLE", "weather_observations")
        self.use_improved_schema = os.getenv("USE_IMPROVED_SCHEMA", "true").lower() == "true"

        self.conn = None
        self.current_job_id = None

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
        """Create database and improved schema tables if missing."""
        self.connect()
        with self.conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{self.database}`")
            cur.execute(f"USE `{self.database}`")

            if self.use_improved_schema:
                # Create all tables in the improved schema
                for schema_sql in get_all_schema_sql():
                    cur.execute(schema_sql)
                logger.info("Ensured improved schema tables exist in %s", self.database)
            else:
                # Legacy single table schema for backward compatibility
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
        """Convert normalized weather data to SQL row format."""
        ts = normalized.get("timestamp")
        # Accept ISO strings or numeric epoch seconds
        if isinstance(ts, (int, float)):
            ts_val = datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        else:
            # attempt to parse ISO-like strings by slicing
            ts_val = ts

        raw_data = normalized.get("raw") or {}
        if isinstance(raw_data, str):
            try:
                raw_data = json.loads(raw_data)
            except:
                raw_data = {}

        # Extract additional fields from raw data if available
        weather_arr = raw_data.get("weather", [{}]) if isinstance(raw_data, dict) else []
        condition_code = weather_arr[0].get("id") if weather_arr else None
        wind_gust = raw_data.get("wind", {}).get("gust") if isinstance(raw_data, dict) else None
        visibility = raw_data.get("visibility") if isinstance(raw_data, dict) else None
        clouds = raw_data.get("clouds", {}).get("all") if isinstance(raw_data, dict) else None
        uv_index = normalized.get("uv_index")
        if uv_index is None and isinstance(raw_data, dict):
            uv_index = raw_data.get("uvi")
            if uv_index is None:
                uv_index = raw_data.get("current", {}).get("uvi") if isinstance(raw_data.get("current"), dict) else None

        if self.use_improved_schema:
            return {
                "city_name": normalized.get("city"),
                "timestamp": ts_val,
                "temperature": normalized.get("temperature"),
                "feels_like": normalized.get("feels_like"),
                "pressure": normalized.get("pressure"),
                "humidity": normalized.get("humidity"),
                "wind_speed": normalized.get("wind_speed"),
                "wind_deg": normalized.get("wind_deg"),
                "wind_gust": wind_gust,
                "condition": normalized.get("condition"),
                "condition_code": condition_code,
                "visibility": visibility,
                "cloudiness": clouds,
                "uv_index": uv_index,
                "raw": json.dumps(raw_data, default=str) if raw_data else "{}",
                "source": "openweathermap",
                "ingestion_job_id": self.current_job_id
            }
        else:
            # Legacy format
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
                "raw": json.dumps(raw_data, default=str) if raw_data else "{}",
                "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            }

    def insert_rows(self, rows: List[Dict], job_id: str = None):
        """Insert rows with improved schema support and job tracking."""
        if not rows:
            return

        if job_id:
            self.current_job_id = job_id
        else:
            # Generate a fresh ingestion job id for each call when not provided.
            self.current_job_id = str(uuid.uuid4())

        self.connect()
        with self.conn.cursor() as cur:
            cur.execute(f"USE `{self.database}`")

            prepared = []
            for r in rows:
                if self.use_improved_schema:
                    rr = self.row_to_sql(r)
                else:
                    if isinstance(r, dict) and "updated_at" in r and "timestamp" in r:
                        rr = r.copy()
                    else:
                        rr = self.row_to_sql(r)

                    raw = rr.get("raw")
                    if isinstance(raw, (dict, list)):
                        rr["raw"] = json.dumps(raw, default=str)
                    else:
                        rr["raw"] = str(raw or "{}")

                prepared.append(rr)

            if not prepared:
                return

            if self.use_improved_schema:
                stage_batch_id = f"batch_{uuid.uuid4().hex}"
                staged_rows = []
                for rr in prepared:
                    staged = rr.copy()
                    staged["ingest_batch_id"] = stage_batch_id
                    if "uv_index" not in staged:
                        staged["uv_index"] = None
                    staged_rows.append(staged)

                stage_insert_sql = """
                INSERT INTO `weather_observations_stage`
                  (ingest_batch_id, city_name, `timestamp`, temperature, feels_like, pressure,
                   humidity, wind_speed, wind_deg, wind_gust, `condition`, condition_code,
                   visibility, cloudiness, uv_index, `raw`, source, ingestion_job_id)
                VALUES
                  (%(ingest_batch_id)s, %(city_name)s, %(timestamp)s, %(temperature)s, %(feels_like)s,
                   %(pressure)s, %(humidity)s, %(wind_speed)s, %(wind_deg)s, %(wind_gust)s, %(condition)s,
                   %(condition_code)s, %(visibility)s, %(cloudiness)s, %(uv_index)s, %(raw)s, %(source)s,
                   %(ingestion_job_id)s)
                ON DUPLICATE KEY UPDATE
                  temperature=VALUES(temperature),
                  feels_like=VALUES(feels_like),
                  pressure=VALUES(pressure),
                  humidity=VALUES(humidity),
                  wind_speed=VALUES(wind_speed),
                  wind_deg=VALUES(wind_deg),
                  wind_gust=VALUES(wind_gust),
                  `condition`=VALUES(`condition`),
                  condition_code=VALUES(condition_code),
                  visibility=VALUES(visibility),
                  cloudiness=VALUES(cloudiness),
                  uv_index=VALUES(uv_index),
                  raw=VALUES(raw),
                  source=VALUES(source),
                  ingestion_job_id=VALUES(ingestion_job_id),
                  stage_loaded_at=CURRENT_TIMESTAMP
                """

                merge_sql = """
                INSERT INTO `weather_observations`
                  (city_name, `timestamp`, temperature, feels_like, pressure, humidity,
                   wind_speed, wind_deg, wind_gust, `condition`, condition_code,
                   visibility, cloudiness, uv_index, `raw`, source, ingestion_job_id)
                SELECT
                  ranked.city_name,
                  ranked.`timestamp`,
                  ranked.temperature,
                  ranked.feels_like,
                  ranked.pressure,
                  ranked.humidity,
                  ranked.wind_speed,
                  ranked.wind_deg,
                  ranked.wind_gust,
                  ranked.`condition`,
                  ranked.condition_code,
                  ranked.visibility,
                  ranked.cloudiness,
                  ranked.uv_index,
                  ranked.`raw`,
                  ranked.source,
                  ranked.ingestion_job_id
                FROM (
                  SELECT
                    ws.city_name,
                    ws.`timestamp`,
                    ws.temperature,
                    ws.feels_like,
                    ws.pressure,
                    ws.humidity,
                    ws.wind_speed,
                    ws.wind_deg,
                    ws.wind_gust,
                    ws.`condition`,
                    ws.condition_code,
                    ws.visibility,
                    ws.cloudiness,
                    ws.uv_index,
                    ws.`raw`,
                    ws.source,
                    ws.ingestion_job_id,
                    ws.stage_loaded_at,
                    ws.id,
                    ROW_NUMBER() OVER (
                      PARTITION BY ws.city_name, ws.`timestamp`
                      ORDER BY ws.stage_loaded_at DESC, ws.id DESC
                    ) AS rn
                  FROM `weather_observations_stage` ws
                  WHERE ws.ingest_batch_id = %s
                ) AS ranked
                WHERE ranked.rn = 1
                ON DUPLICATE KEY UPDATE
                  temperature=VALUES(temperature),
                  feels_like=VALUES(feels_like),
                  pressure=VALUES(pressure),
                  humidity=VALUES(humidity),
                  wind_speed=VALUES(wind_speed),
                  wind_deg=VALUES(wind_deg),
                  wind_gust=VALUES(wind_gust),
                  `condition`=VALUES(`condition`),
                  condition_code=VALUES(condition_code),
                  visibility=VALUES(visibility),
                  cloudiness=VALUES(cloudiness),
                  uv_index=VALUES(uv_index),
                  raw=VALUES(raw),
                  source=VALUES(source),
                  ingestion_job_id=VALUES(ingestion_job_id),
                  updated_at=CURRENT_TIMESTAMP
                """

                cleanup_sql = """
                DELETE FROM `weather_observations_stage`
                WHERE ingest_batch_id = %s
                """

                prev_autocommit = bool(getattr(self.conn, "autocommit_mode", True))
                if prev_autocommit:
                    self.conn.autocommit(False)

                try:
                    cur.execute("START TRANSACTION")
                    cur.executemany(stage_insert_sql, staged_rows)
                    cur.execute(merge_sql, (stage_batch_id,))
                    cur.execute(cleanup_sql, (stage_batch_id,))
                    self.conn.commit()
                    logger.info(
                        "Upserted %d rows via staging batch %s into weather_observations",
                        len(staged_rows),
                        stage_batch_id,
                    )
                except Exception:
                    self.conn.rollback()
                    logger.exception("Failed to merge staging batch %s", stage_batch_id)
                    raise
                finally:
                    if prev_autocommit:
                        self.conn.autocommit(True)
            else:
                insert_sql = f"""
                INSERT INTO `{self.table}`
                  (city, `timestamp`, temperature, feels_like, pressure, humidity, wind_speed, wind_deg, `condition`, `raw`, updated_at)
                VALUES
                  (%(city)s, %(timestamp)s, %(temperature)s, %(feels_like)s, %(pressure)s, %(humidity)s, %(wind_speed)s, %(wind_deg)s, %(condition)s, %(raw)s, %(updated_at)s)
                ON DUPLICATE KEY UPDATE
                  temperature=VALUES(temperature), feels_like=VALUES(feels_like), pressure=VALUES(pressure), humidity=VALUES(humidity),
                  wind_speed=VALUES(wind_speed), wind_deg=VALUES(wind_deg), `condition`=VALUES(`condition`), raw=VALUES(raw), updated_at=VALUES(updated_at)
                """
                cur.executemany(insert_sql, prepared)
                logger.info("Inserted/updated %d legacy rows into %s.%s", len(rows), self.database, self.table)

    def get_latest_weather(self, city: str) -> Dict:
        """Get latest weather observation for a city."""
        self.connect()
        with self.conn.cursor() as cur:
            cur.execute(f"USE `{self.database}`")
            if self.use_improved_schema:
                cur.execute("""
                    SELECT * FROM `weather_observations` 
                    WHERE city_name=%s 
                    ORDER BY `timestamp` DESC 
                    LIMIT 1
                """, (city,))
            else:
                cur.execute(f"SELECT * FROM `{self.table}` WHERE city=%s ORDER BY `timestamp` DESC LIMIT 1", (city,))
            row = cur.fetchone()
            # Map city_name back to city for backward compatibility
            if row and self.use_improved_schema and 'city_name' in row:
                row['city'] = row['city_name']
            return row or {}

    def get_weather_history(self, city: str, days: int = 7) -> List[Dict]:
        """Get weather history for a city over specified days."""
        self.connect()
        with self.conn.cursor() as cur:
            cur.execute(f"USE `{self.database}`")
            if self.use_improved_schema:
                cur.execute("""
                    SELECT * FROM `weather_observations` 
                    WHERE city_name=%s AND `timestamp` >= NOW() - INTERVAL %s DAY 
                    ORDER BY `timestamp` DESC
                """, (city, int(days)))
            else:
                cur.execute(f"SELECT * FROM `{self.table}` WHERE city=%s AND `timestamp` >= NOW() - INTERVAL %s DAY ORDER BY `timestamp` DESC", (city, int(days)))
            rows = cur.fetchall()
            # Map city_name back to city for backward compatibility
            if self.use_improved_schema:
                for row in rows:
                    if 'city_name' in row:
                        row['city'] = row['city_name']
            return rows
    
    def upsert_city(self, city_name: str, country: str = None, country_code: str = None,
                    latitude: float = None, longitude: float = None, **kwargs) -> Optional[int]:
        """Insert or update city metadata, returns city_id."""
        if not self.use_improved_schema:
            return None
        
        self.connect()
        with self.conn.cursor() as cur:
            cur.execute(f"USE `{self.database}`")
            # Try to get existing city
            cur.execute("SELECT id FROM cities WHERE name=%s", (city_name,))
            existing = cur.fetchone()
            
            if existing:
                city_id = existing['id']
                # Update if new data provided
                if any([country, country_code, latitude, longitude]):
                    update_fields = []
                    params = []
                    if country:
                        update_fields.append("country=%s")
                        params.append(country)
                    if country_code:
                        update_fields.append("country_code=%s")
                        params.append(country_code)
                    if latitude is not None:
                        update_fields.append("latitude=%s")
                        params.append(latitude)
                    if longitude is not None:
                        update_fields.append("longitude=%s")
                        params.append(longitude)
                    if update_fields:
                        params.append(city_name)
                        cur.execute(f"UPDATE cities SET {', '.join(update_fields)} WHERE name=%s", params)
            else:
                # Insert new city
                cur.execute("""
                    INSERT INTO cities (name, country, country_code, latitude, longitude)
                    VALUES (%s, %s, %s, %s, %s)
                """, (city_name, country, country_code, latitude, longitude))
                city_id = cur.lastrowid
            
            return city_id
    
    def log_ingestion_job(self, job_id: str, job_type: str, status: str, 
                          started_at: datetime, completed_at: datetime = None,
                          cities_processed: int = 0, records_inserted: int = 0,
                          records_updated: int = 0, records_failed: int = 0,
                          error_message: str = None, metadata: Dict = None):
        """Log an ingestion job to ingestion_logs table."""
        if not self.use_improved_schema:
            return
        
        self.connect()
        with self.conn.cursor() as cur:
            cur.execute(f"USE `{self.database}`")
            duration = None
            if completed_at and started_at:
                duration = int((completed_at - started_at).total_seconds())
            
            cur.execute("""
                INSERT INTO ingestion_logs 
                (job_id, job_type, status, started_at, completed_at, duration_seconds,
                 cities_processed, records_inserted, records_updated, records_failed,
                 error_message, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                status=VALUES(status), completed_at=VALUES(completed_at),
                duration_seconds=VALUES(duration_seconds), cities_processed=VALUES(cities_processed),
                records_inserted=VALUES(records_inserted), records_updated=VALUES(records_updated),
                records_failed=VALUES(records_failed), error_message=VALUES(error_message),
                metadata=VALUES(metadata)
            """, (job_id, job_type, status, started_at, completed_at, duration,
                  cities_processed, records_inserted, records_updated, records_failed,
                  error_message, json.dumps(metadata) if metadata else None))
        
        logger.info("Logged ingestion job: %s (%s) - %s", job_id, job_type, status)
