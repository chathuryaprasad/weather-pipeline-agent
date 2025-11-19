"""Shared services and helpers for the API layer."""

from __future__ import annotations

import logging
from threading import Lock

from agent.weather_agent import WeatherAgent
from config.settings import settings

logger = logging.getLogger(__name__)

_agent_lock = Lock()
_agent_instance: WeatherAgent | None = None


def get_weather_agent() -> WeatherAgent:
    """Return a singleton WeatherAgent instance."""
    global _agent_instance

    if not settings.OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured. Set it before using the agent endpoint."
        )

    if _agent_instance is None:
        with _agent_lock:
            if _agent_instance is None:
                logger.info("Initializing WeatherAgent singleton")
                _agent_instance = WeatherAgent()

    return _agent_instance

