## Example queries & sample responses

## Call the REST API

### Health check
```bash
curl -H "Authorization: Bearer $API_TOKEN" \
     "$API_URL/health"
```   
```bash
{
    "status": "ok"
}
```

## Agent query

### What was the average temperature in Galle last week?
```bash
curl -H "Authorization: Bearer $API_AUTH_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"query": "What was the average temperature in Galle last week?"}' \
     http://localhost:8000/api/agent/query
```

```bash
{
    "query": "What was the average temperature in Galle last week?",
    "response": "The average temperature in Galle last week was 28.34°C, with a minimum of 26.56°C and a maximum of 30.52°C. If you have any more weather questions, feel free to ask!"
}
```

### What is the current weather in Colombo?
```bash
{
    "query": "What is the current weather in Colombo?",
    "response": "The current weather in Colombo is as follows:\n- Temperature: 26.13°C\n- Condition: Moderate rain\n- Humidity: 94%\n- Wind Speed: 3.76 m/s\n- Pressure: 1010 hPa\n- Feels Like: 26.13°C\n\nIf you have any more questions about the weather, feel free to ask!"
}
```
### Did Kandy experience any rainy conditions yesterday?
```bash
{
    "query": "Did Kandy experience any rainy conditions yesterday?",
    "response": "Yes, Kandy experienced rainy conditions yesterday. The weather included moderate rain in the morning, with a temperature of 26.27°C and humidity at 79%. Later, there were light rain conditions with a temperature of 21.95°C and humidity reaching 96%."
}
```

### What was the highest temperature recorded in Jaffna this month?
```bash
{
    "query": "What was the highest temperature recorded in Jaffna this month?",
    "response": "The highest temperature recorded in Jaffna this month was 28.03°C. If you need more weather information, feel free to ask!"
}
```
## (Guardrail Example)
### Who won the cricket match yesterday? 
```bash
{
    "query": "Who won the cricket match yesterday?",
    "response": "I'm a weather assistant specialized in answering questions about weather conditions, \ntemperatures, forecasts, and climate data for cities around the world. \n\nI can help you with:\n- Current weather conditions in any city\n- Historical weather data and trends\n- Temperature averages and statistics\n- Weather comparisons between cities\n\nI'm not able to answer questions outside of weather and climate topics. If you have a weather-related question, \nI'd be happy to help!"
}
```


### Latest weather 
```bash 
curl -H "Authorization: Bearer $API_AUTH_TOKEN" \
     "http://localhost:8000/api/weather/latest?city=Colombo"
```
```bash
{
    "city": "Colombo",
    "data": {
        "id": 6201,
        "city_name": "Colombo",
        "timestamp": "2025-11-21T12:26:41",
        "temperature": 26.13,
        "feels_like": 26.13,
        "pressure": 1010,
        "humidity": 94,
        "wind_speed": 3.76,
        "wind_deg": 351,
        "wind_gust": 4.13,
        "condition": "moderate rain",
        "condition_code": "501",
        "visibility": 2286,
        "cloudiness": 81,
        "raw": "{\"dt\": 1763728001, \"id\": 1248991, \"cod\": 200, \"sys\": {\"id\": 2103021, \"type\": 2, \"sunset\": 1763727605, \"country\": \"LK\", \"sunrise\": 1763685188}, \"base\": \"stations\", \"main\": {\"temp\": 26.13, \"humidity\": 94, \"pressure\": 1010, \"temp_max\": 26.13, \"temp_min\": 25.97, \"sea_level\": 1010, \"feels_like\": 26.13, \"grnd_level\": 1009}, \"name\": \"Colombo\", \"rain\": {\"1h\": 1.54}, \"wind\": {\"deg\": 351, \"gust\": 4.13, \"speed\": 3.76}, \"coord\": {\"lat\": 6.9319, \"lon\": 79.8478}, \"clouds\": {\"all\": 81}, \"weather\": [{\"id\": 501, \"icon\": \"10n\", \"main\": \"Rain\", \"description\": \"moderate rain\"}], \"timezone\": 19800, \"visibility\": 2286}",
        "source": "openweathermap",
        "ingestion_job_id": "ingest_20251121_123403_9309e1eb",
        "created_at": "2025-11-21T12:36:13",
        "updated_at": "2025-11-21T12:36:13",
        "city": "Colombo"
    }
}
```
### Weather history
```bash
curl --location 'http://localhost:8000/api/weather/history?city=Badulla&days=2' \
--header 'Authorization: Bearer $API_AUTH_TOKEN'
```

```bash
{
    "city": "Badulla",
    "days": 2,
    "results": [
        {
            "id": 6316,
            "city_name": "Badulla",
            "timestamp": "2025-11-21T13:34:23",
            "temperature": 21.26,
            "feels_like": 21.95,
            "pressure": 1015,
            "humidity": 96,
            "wind_speed": 0.99,
            "wind_deg": 323,
            "wind_gust": 0.81,
            "condition": "overcast clouds",
            "condition_code": "804",
            "visibility": 10000,
            "cloudiness": 99,
            "raw": "{\"dt\": 1763732063, \"id\": 1250615, \"cod\": 200, \"sys\": {\"sunset\": 1763727310, \"country\": \"LK\", \"sunrise\": 1763684903}, \"base\": \"stations\", \"main\": {\"temp\": 21.26, \"humidity\": 96, \"pressure\": 1015, \"temp_max\": 21.26, \"temp_min\": 21.26, \"sea_level\": 1015, \"feels_like\": 21.95, \"grnd_level\": 918}, \"name\": \"Badulla\", \"wind\": {\"deg\": 323, \"gust\": 0.81, \"speed\": 0.99}, \"coord\": {\"lat\": 6.9895, \"lon\": 81.0557}, \"clouds\": {\"all\": 99}, \"weather\": [{\"id\": 804, \"icon\": \"04n\", \"main\": \"Clouds\", \"description\": \"overcast clouds\"}], \"timezone\": 19800, \"visibility\": 10000}",
            "source": "openweathermap",
            "ingestion_job_id": "ingest_20251121_133403_0f092229",
            "created_at": "2025-11-21T13:36:18",
            "updated_at": "2025-11-21T13:36:18",
            "city": "Badulla"
        },
        {
            "id": 6016,
            "city_name": "Badulla",
            "timestamp": "2025-11-20T08:31:54",
            "temperature": 25.56,
            "feels_like": 26.13,
            "pressure": 1011,
            "humidity": 75,
            "wind_speed": 2.79,
            "wind_deg": 36,
            "wind_gust": 2.74,
            "condition": "overcast clouds",
            "condition_code": "804",
            "visibility": 10000,
            "cloudiness": 87,
            "raw": "{\"dt\": 1763713933, \"id\": 1250615, \"cod\": 200, \"sys\": {\"sunset\": 1763727310, \"country\": \"LK\", \"sunrise\": 1763684903}, \"base\": \"stations\", \"main\": {\"temp\": 25.56, \"humidity\": 75, \"pressure\": 1011, \"temp_max\": 25.56, \"temp_min\": 25.56, \"sea_level\": 1011, \"feels_like\": 26.13, \"grnd_level\": 915}, \"name\": \"Badulla\", \"wind\": {\"deg\": 36, \"gust\": 2.74, \"speed\": 2.79}, \"coord\": {\"lat\": 6.9895, \"lon\": 81.0557}, \"clouds\": {\"all\": 87}, \"weather\": [{\"id\": 804, \"icon\": \"04d\", \"main\": \"Clouds\", \"description\": \"overcast clouds\"}], \"timezone\": 19800, \"visibility\": 10000}",
            "source": "openweathermap",
            "ingestion_job_id": "ingest_20251121_083154_f4b6321c",
            "created_at": "2025-11-21T08:34:03",
            "updated_at": "2025-11-21T08:34:03",
            "city": "Badulla"
        }
    ]
}
```

