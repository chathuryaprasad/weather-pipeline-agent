import os
from dotenv import load_dotenv
from ingestion.loader_bigquery import BigQueryLoader
from ingestion.weather_client import WeatherClient

load_dotenv()

API_KEY = os.getenv("OPENWEATHER_API_KEY")
CITIES = [
    "Colombo", "Galle", "Kandy", "Jaffna", "Matara", "Anuradhapura", 
    "Trincomalee", "Hambantota", "Negombo", "Ratnapura"
] 

# Initialize clients
bq_loader = BigQueryLoader()
bq_loader.ensure_table()

weather_client = WeatherClient(API_KEY)

# Fetch weather
raw_data = weather_client.fetch_multiple_cities(CITIES)

# Normalize
normalized = [weather_client.normalize_weather(d) for d in raw_data]

# Convert to BigQuery rows
rows = [bq_loader.row_to_bq(r) for r in normalized]

# Insert into BigQuery
bq_loader.insert_rows(rows)

print("Weather ingestion completed successfully!")
