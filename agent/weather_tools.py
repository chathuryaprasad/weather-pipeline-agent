"""Custom tools for the AI agent to query weather data."""
from typing import Dict, List, Any
from datetime import datetime, date
import logging
from ingestion.store import get_latest_weather, get_weather_history
from ingestion.weather_client import WeatherClient
from config.settings import settings

logger = logging.getLogger(__name__)

# Initialize weather client for fallback
_weather_client = None

def _get_weather_client():
    """Lazy initialization of weather client for fallback."""
    global _weather_client
    if _weather_client is None and settings.OPENWEATHER_API_KEY:
        _weather_client = WeatherClient(settings.OPENWEATHER_API_KEY)
    return _weather_client


def _convert_datetime_to_str(obj):
    """Recursively convert datetime objects to ISO format strings."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: _convert_datetime_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_datetime_to_str(item) for item in obj]
    else:
        return obj


def get_current_weather_tool(city: str) -> Dict[str, Any]:
    """
    Get the current (latest) weather data for a specific city.
    Falls back to OpenWeatherMap API if database query fails.
    
    Args:
        city: The name of the city (e.g., "Colombo", "Galle", "London")
    
    Returns:
        A dictionary containing weather information including:
        - city: City name
        - timestamp: When the data was recorded
        - temperature: Temperature in Celsius
        - condition: Weather condition description
        - humidity: Humidity percentage
        - wind_speed: Wind speed
        - pressure: Atmospheric pressure
        - feels_like: Feels-like temperature
    """
    # Try database first
    try:
        weather = get_latest_weather(city)
        if weather:
            # Format the response for the agent
            result = {
                "city": weather.get("city", city),
                "timestamp": weather.get("timestamp"),
                "temperature": weather.get("temperature"),
                "condition": weather.get("condition"),
                "humidity": weather.get("humidity"),
                "wind_speed": weather.get("wind_speed"),
                "pressure": weather.get("pressure"),
                "feels_like": weather.get("feels_like"),
                "wind_deg": weather.get("wind_deg"),
                "source": "database"
            }
            # Convert datetime objects to strings
            return _convert_datetime_to_str(result)
    except Exception as e:
        logger.warning(f"Database query failed for {city}, falling back to OpenWeatherMap API: {e}")
    
    # Fallback to OpenWeatherMap API
    try:
        weather_client = _get_weather_client()
        if not weather_client:
            return {
                "error": f"No weather data found for {city} and OpenWeatherMap API key not configured",
                "city": city
            }
        
        raw_data = weather_client.fetch_city_weather(city)
        if not raw_data:
            return {
                "error": f"No weather data found for {city}",
                "city": city
            }
        
        # Normalize the API response
        normalized = weather_client.normalize_weather(raw_data)
        
        result = {
            "city": normalized.get("city", city),
            "timestamp": normalized.get("timestamp"),
            "temperature": normalized.get("temperature"),
            "condition": normalized.get("condition"),
            "humidity": normalized.get("humidity"),
            "wind_speed": normalized.get("wind_speed"),
            "pressure": normalized.get("pressure"),
            "feels_like": normalized.get("feels_like"),
            "wind_deg": normalized.get("wind_deg"),
            "source": "openweathermap_api"
        }
        # Convert datetime objects to strings
        return _convert_datetime_to_str(result)
    except Exception as e:
        logger.exception(f"Error fetching current weather for {city} from API: {e}")
        return {"error": f"Failed to fetch weather data for {city}: {str(e)}"}


def get_weather_history_tool(city: str, days: int = 7) -> Dict[str, Any]:
    """
    Get historical weather data for a specific city over a specified number of days.
    
    Args:
        city: The name of the city
        days: Number of days of history to retrieve (default: 7)
    
    Returns:
        A dictionary containing:
        - city: City name
        - days: Number of days requested
        - records: List of weather records
        - count: Number of records found
    """
    try:
        history = get_weather_history(city, days=days)
        if not history:
            return {
                "error": f"No historical weather data found for {city}",
                "city": city,
                "days": days,
                "count": 0
            }
        
        # Format records for readability
        records = []
        for record in history:
            records.append({
                "timestamp": record.get("timestamp"),
                "temperature": record.get("temperature"),
                "condition": record.get("condition"),
                "humidity": record.get("humidity"),
                "wind_speed": record.get("wind_speed"),
                "pressure": record.get("pressure")
            })
        
        result = {
            "city": city,
            "days": days,
            "count": len(records),
            "records": records
        }
        # Convert datetime objects to strings
        return _convert_datetime_to_str(result)
    except Exception as e:
        logger.exception(f"Error fetching weather history for {city}: {e}")
        return {"error": f"Failed to fetch weather history for {city}: {str(e)}"}


def calculate_average_temperature_tool(city: str, days: int = 7) -> Dict[str, Any]:
    """
    Calculate the average temperature for a city over a specified number of days.
    
    Args:
        city: The name of the city
        days: Number of days to calculate average over (default: 7)
    
    Returns:
        A dictionary containing:
        - city: City name
        - days: Number of days
        - average_temperature: Average temperature in Celsius
        - min_temperature: Minimum temperature
        - max_temperature: Maximum temperature
        - count: Number of records used
    """
    try:
        history = get_weather_history(city, days=days)
        if not history:
            return {
                "error": f"No weather data found for {city} to calculate average",
                "city": city,
                "days": days
            }
        
        temperatures = [r.get("temperature") for r in history if r.get("temperature") is not None]
        
        if not temperatures:
            return {
                "error": f"No temperature data available for {city}",
                "city": city,
                "days": days
            }
        
        avg_temp = sum(temperatures) / len(temperatures)
        min_temp = min(temperatures)
        max_temp = max(temperatures)
        
        return {
            "city": city,
            "days": days,
            "average_temperature": round(avg_temp, 2),
            "min_temperature": round(min_temp, 2),
            "max_temperature": round(max_temp, 2),
            "count": len(temperatures)
        }
    except Exception as e:
        logger.exception(f"Error calculating average temperature for {city}: {e}")
        return {"error": f"Failed to calculate average temperature for {city}: {str(e)}"}

