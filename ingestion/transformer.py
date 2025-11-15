# ingestion/transformer.py
from datetime import datetime, timezone
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def normalize_current_weather(owm_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert OWM current weather response into canonical dict.
    Assumes use of 'units' param (metric/imperial) in API client.
    """
    if not owm_json:
        raise ValueError("Empty input to normalize_current_weather")

    # City name (fall back to name field)
    city = owm_json.get("name") or owm_json.get("sys", {}).get("country", "unknown")

    # Timestamp: use 'dt' field (UTC seconds) and convert to ISO
    dt = owm_json.get("dt")
    if dt:
        ts = datetime.fromtimestamp(dt, tz=timezone.utc).isoformat()
    else:
        ts = datetime.now(timezone.utc).isoformat()

    main = owm_json.get("main", {})
    wind = owm_json.get("wind", {})
    weather_arr = owm_json.get("weather") or []
    condition = weather_arr[0].get("description") if weather_arr else None

    normalized = {
        "city": city,
        "timestamp": ts,
        "temperature": main.get("temp"),
        "feels_like": main.get("feels_like"),
        "pressure": main.get("pressure"),
        "humidity": main.get("humidity"),
        "wind_speed": wind.get("speed"),
        "wind_deg": wind.get("deg"),
        "condition": condition,
        "raw": owm_json
    }

    # Validate essential fields
    if normalized["temperature"] is None:
        logger.warning("Temperature missing for city %s: payload keys: %s", city, list(owm_json.keys()))

    return normalized
