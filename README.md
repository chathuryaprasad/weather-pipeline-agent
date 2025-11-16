python -m scripts.run_pipeline

$env:GOOGLE_APPLICATION_CREDENTIALS = 'D:\J\Add up\Task\adup-task-3e9f1956c836.json'




#Count configured cities:
python -c "import json; print('cities=', len(json.load(open('config/cities_list.json'))))"


#Fetch a single city (verify networking & API key):
python -c "from ingestion.weather_client import WeatherClient; import os; c=WeatherClient(os.getenv('OPENWEATHER_API_KEY')); print(c.fetch_city_weather('London'))"


#One-shot pipeline run (end-to-end):
python -m scripts.run_pipeline


#Idempotency test
Run the pipeline twice in a row:

python -m scripts.run_pipeline
python -m scripts.run_pipeline


#Run scheduler only (no backfill):
$env:BACKFILL_DAYS = '0'
python -m scripts.orchestrator


# Run scheduler only (no backfill):
$env:BACKFILL_DAYS = '0'
python -m scripts.orchestrator

# To run backfill for N days:
$env:BACKFILL_DAYS = '7'  # backfill 7 days
python -m scripts.orchestrator

