from google.cloud import bigquery
from google.api_core.exceptions import NotFound, Forbidden
from typing import Dict, List
import logging
import json
import os
import io
from datetime import datetime,timezone
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

        creds_env = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if creds_env and creds_env.startswith("GOOGLE_APPLICATION_CREDENTIALS="):
            fixed = creds_env.split("=", 1)[1]
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = fixed
            logger.warning("Sanitized GOOGLE_APPLICATION_CREDENTIALS env var (removed prefix).")

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

        # Fallback: perform a load job using newline-delimited JSON in-memory.
        try:
            logger.info("Falling back to load job for %d rows", len(rows))
            ndjson = io.BytesIO()
            for r in rows:
                ndjson.write((json.dumps(r, default=str) + "\n").encode("utf-8"))
            ndjson.seek(0)

            job_config = bigquery.LoadJobConfig()
            job_config.source_format = bigquery.SourceFormat.NEWLINE_DELIMITED_JSON
            job_config.schema = SCHEMA
            job_config.write_disposition = bigquery.WriteDisposition.WRITE_APPEND

            load_job = self.client.load_table_from_file(ndjson, table, job_config=job_config)
            result = load_job.result()  # wait
            logger.info("Load job finished: %s, loaded %d rows", load_job.job_id, result.output_rows)
            return None
        except Exception as ex:
            logger.exception("Fallback load job failed: %s", ex)
            raise
