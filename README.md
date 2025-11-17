Run Test
python -m pytest -q
# or single check:
python -c "from ingestion.transformer import normalize_current_weather; sample={'name':'X','dt':1600000000,'main':{'temp':10},'wind':{'speed':1},'weather':[{'description':'clear'}]}; out=normalize_current_weather(sample); assert out['city']=='X' and 'timestamp' in out and out['temperature']==10; print('transformer OK')"


##################################################################################################
one-shot ingest

echo $env:OPENWEATHER_API_KEY
echo $env:GOOGLE_APPLICATION_CREDENTIALS
echo $env:GCP_PROJECT_ID
echo $env:BIGQUERY_DATASET
echo $env:BIGQUERY_TABLE
echo $env:BACKFILL_DAYS


python -c "from ingestion.loader_bigquery import BigQueryLoader; bq=BigQueryLoader(); bq.ensure_table(); print('ensure_table OK')"

python -c "from scripts.run_pipeline import fetch_and_store_weather; fetch_and_store_weather(); print('one-shot ingest attempted')"

####################################################################################################


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

