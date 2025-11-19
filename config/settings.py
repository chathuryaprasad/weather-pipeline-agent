# config/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(env_path)

class Settings:
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    API_AUTH_TOKEN: str = os.getenv("API_AUTH_TOKEN", "")
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "")
    BIGQUERY_DATASET: str = os.getenv("BIGQUERY_DATASET", "weather_dataset")
    BIGQUERY_TABLE: str = os.getenv("BIGQUERY_TABLE", "weather_data")
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    DEFAULT_UNITS: str = os.getenv("DEFAULT_UNITS", "metric")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    BACKFILL_MONTHS: int = int(os.getenv("BACKFILL_MONTHS", "2"))

settings = Settings()
