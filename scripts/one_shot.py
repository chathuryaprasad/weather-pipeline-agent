# scripts/one_shot.py
from scripts.run_pipeline import fetch_and_store_weather
if __name__ == "__main__":
    fetch_and_store_weather()
    print("one-shot ingest attempted")