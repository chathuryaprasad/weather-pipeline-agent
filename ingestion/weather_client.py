import requests
import time
import logging
from typing import Dict, List

from ingestion.transformer import normalize_current_weather

logger = logging.getLogger(__name__)


class WeatherClient:
    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def fetch_city_weather(self, city: str) -> Dict:
        """Fetch current weather for a single city."""
        params = {
            "q": city,
            "appid": self.api_key,
            "units": "metric"
        }
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error("Error fetching weather for %s: %s", city, e)
            return {}

    def fetch_multiple_cities(self, cities: List[str], delay: float = 1.0) -> List[Dict]:
        """Fetch weather for multiple cities with optional delay to avoid rate limits."""
        all_data = []
        for city in cities:
            data = self.fetch_city_weather(city)
            if data:
                all_data.append(data)
            time.sleep(delay)
        return all_data

    @staticmethod
    def normalize_weather(data: Dict) -> Dict:
        """Normalize an OpenWeatherMap response using the shared transformer.

        Returns the canonical dict with ISO timestamp string and canonical fields.
        """
        if not data:
            return {}
        try:
            return normalize_current_weather(data)
        except Exception:
            # Fallback to a simple extraction if transformer fails
            weather = data.get("weather", [{}])[0]
            main = data.get("main", {})
            wind = data.get("wind", {})
            return {
                "city": data.get("name"),
                "timestamp": data.get("dt"),
                "temperature": main.get("temp"),
                "feels_like": main.get("feels_like"),
                "pressure": main.get("pressure"),
                "humidity": main.get("humidity"),
                "wind_speed": wind.get("speed"),
                "wind_deg": wind.get("deg"),
                "condition": weather.get("description"),
                "raw": data
            }


# NOTE: previously this module executed example code at import time which
# triggered network/API calls and blocking behavior. Keep this module free of
# side-effects so it is safe to `import` in scripts and tests.
