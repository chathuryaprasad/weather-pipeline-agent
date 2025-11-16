import os
# Defensive sanitizer: some Windows users accidentally set the environment value
# to the literal string "GOOGLE_APPLICATION_CREDENTIALS=path..." (including
# the key name). Fix it as early as possible (before importing google libs).
creds_env = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
if creds_env and creds_env.startswith("GOOGLE_APPLICATION_CREDENTIALS="):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_env.split("=", 1)[1]

from google.cloud import bigquery
from google.api_core.exceptions import NotFound, Forbidden
from typing import Dict, List
import logging
import json
import io
from datetime import datetime,timezone
import uuid
from config.settings import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

SCHEMA = [
    bigquery.SchemaField("city", "STRING"),
    bigquery.SchemaField("timestamp", "TIMESTAMP"),
    bigquery.SchemaField("temperature", "FLOAT"),
    bigquery.SchemaField("feels_like", "FLOAT"),
    bigquery.SchemaField("pressure", "INTEGER"),
    bigquery.SchemaField("humidity", "INTEGER"),
    bigquery.SchemaField("wind_speed", "FLOAT"),
    bigquery.SchemaField("wind_deg", "INTEGER"),
    bigquery.SchemaField("condition", "STRING"),
    bigquery.SchemaField("raw", "STRING"),
    bigquery.SchemaField("updated_at", "TIMESTAMP")
]

class BigQueryLoader:
    def __init__(self, project: str = None, dataset: str = None, table: str = None):
        self.project = project or settings.GCP_PROJECT_ID
        self.dataset = dataset or settings.BIGQUERY_DATASET
        self.table = table or settings.BIGQUERY_TABLE

        self.client = bigquery.Client(project=self.project)
        self.table_ref = self.client.dataset(self.dataset).table(self.table)

    def ensure_table(self):
        dataset_ref = self.client.dataset(self.dataset)
        # Create dataset if missing
        try:
            self.client.get_dataset(dataset_ref)
        except NotFound:
            logger.info("Dataset %s not found; creating.", self.dataset)
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = "US"
            self.client.create_dataset(dataset)

        # Create table if missing
        try:
            self.client.get_table(self.table_ref)
            logger.debug("Table exists: %s.%s", self.dataset, self.table)
        except NotFound:
            logger.info("Table %s.%s not found; creating with schema.", self.dataset, self.table)
            table = bigquery.Table(self.table_ref, schema=SCHEMA)
            table = self.client.create_table(table)
            logger.info("Created table %s", table.full_table_id)

    def row_to_bq(self, normalized: Dict) -> Dict:
        row = {
            "city": normalized.get("city"),
            "timestamp": normalized.get("timestamp"),
            "temperature": normalized.get("temperature"),
            "feels_like": normalized.get("feels_like"),
            "pressure": normalized.get("pressure"),
            "humidity": normalized.get("humidity"),
            "wind_speed": normalized.get("wind_speed"),
            "wind_deg": normalized.get("wind_deg"),
            "condition": normalized.get("condition"),
            "raw": json.dumps(normalized.get("raw", {})),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        return row

    def insert_rows(self, rows: List[Dict]):
        if not rows:
            return
        table = self.client.get_table(self.table_ref)
        try:
            errors = self.client.insert_rows_json(
                table,
                rows,
                row_ids=[f"{r['city']}|{r['timestamp']}" for r in rows]
            )
            if errors:
                logger.error("Insert errors: %s", errors)
            else:
                logger.info("Inserted %d rows successfully", len(rows))
            return
        except Forbidden as fb:
            # Common in projects on the free tier: streaming inserts are disabled.
            logger.warning("Streaming insert forbidden: %s - falling back to load job.", fb)
        except Exception as e:
            logger.exception("Failed to insert rows (streaming): %s", e)

        # Fallback: perform a MERGE-based upsert to guarantee idempotency.
        try:
            logger.info("Falling back to MERGE upsert for %d rows", len(rows))
            self.merge_upsert(rows)
            return
        except Exception as ex:
            logger.exception("Fallback merge_upsert failed: %s", ex)
            raise

    def merge_upsert(self, rows: List[Dict]):
        """
        Load rows into a temporary table and MERGE into the main table using
        (city, timestamp) as the deduplication key. This provides idempotency
        for repeated runs and avoids duplicate rows when streaming inserts are
        not allowed.
        """
        if not rows:
            return

        temp_table_name = f"temp_ingest_{uuid.uuid4().hex}"
        temp_table_ref = self.client.dataset(self.dataset).table(temp_table_name)

        # Prepare NDJSON in-memory
        ndjson = io.BytesIO()
        for r in rows:
            ndjson.write((json.dumps(r, default=str) + "\n").encode("utf-8"))
        ndjson.seek(0)

        # Load into temp table
        job_config = bigquery.LoadJobConfig()
        job_config.source_format = bigquery.SourceFormat.NEWLINE_DELIMITED_JSON
        job_config.schema = SCHEMA
        job_config.write_disposition = bigquery.WriteDisposition.WRITE_TRUNCATE

        logger.info("Creating temp table %s and loading %d rows", temp_table_name, len(rows))
        load_job = self.client.load_table_from_file(ndjson, temp_table_ref, job_config=job_config)
        load_result = load_job.result()
        logger.info("Temp load finished: %s, rows: %d", load_job.job_id, load_result.output_rows)

        # MERGE temp into target table using city+timestamp as key
        target = f"`{self.project}.{self.dataset}.{self.table}`"
        source = f"`{self.project}.{self.dataset}.{temp_table_name}`"

        cols = [f.name for f in SCHEMA]
        # Exclude key columns from update set
        update_set = ", ".join([f"T.{c} = S.{c}" for c in cols if c not in ("city", "timestamp")])
        insert_cols = ", ".join(cols)
        insert_vals = ", ".join([f"S.{c}" for c in cols])

        merge_sql = f"""
        MERGE {target} T
        USING {source} S
        ON T.city = S.city AND T.timestamp = S.timestamp
        WHEN MATCHED THEN
          UPDATE SET {update_set}
        WHEN NOT MATCHED THEN
          INSERT ({insert_cols})
          VALUES ({insert_vals})
        """

        logger.info("Running MERGE into %s from %s", self.table, temp_table_name)
        query_job = self.client.query(merge_sql)
        query_job.result()
        logger.info("MERGE completed: %s", query_job.job_id)

        # Cleanup
        try:
            self.client.delete_table(temp_table_ref)
            logger.info("Deleted temp table %s", temp_table_name)
        except Exception:
            logger.warning("Failed to delete temp table %s; leaving for retention cleanup.", temp_table_name)

    def get_latest_weather(self, city: str) -> Dict:
        """
        Return the most recent weather row for `city` as a dict, or {} if none.
        """
        target = f"`{self.project}.{self.dataset}.{self.table}`"
        sql = f"SELECT * FROM {target} WHERE city = @city ORDER BY timestamp DESC LIMIT 1"
        job_config = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter("city", "STRING", city)])
        query_job = self.client.query(sql, job_config=job_config)
        rows = list(query_job.result())
        if not rows:
            return {}
        row = rows[0]
        # Convert Row to native dict
        return {k: row[k] for k in row.keys()}

    def get_weather_history(self, city: str, days: int = 7) -> List[Dict]:
        """
        Return weather history for `city` for the past `days` days (inclusive), ordered newest-first.
        """
        target = f"`{self.project}.{self.dataset}.{self.table}`"
        sql = (
            f"SELECT * FROM {target} WHERE city = @city "
            f"AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY) "
            f"ORDER BY timestamp DESC"
        )
        job_config = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("city", "STRING", city),
            bigquery.ScalarQueryParameter("days", "INT64", int(days)),
        ])
        query_job = self.client.query(sql, job_config=job_config)
        results = []
        for r in query_job.result():
            results.append({k: r[k] for k in r.keys()})
        return results
