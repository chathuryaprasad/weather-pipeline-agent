"""FastAPI application exposing weather data and agent endpoints."""

from __future__ import annotations

import logging
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from agent.weather_agent import WeatherAgent
from ingestion.store import get_latest_weather, get_weather_history

from .schemas import (
    AgentQueryRequest,
    AgentQueryResponse,
    HealthResponse,
    WeatherHistoryResponse,
    WeatherLatestResponse,
)
from .security import verify_bearer_token
from .services import get_weather_agent
from .utils import serialize_record, serialize_records

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Weather Agent API",
    description="REST API for querying weather observations and interacting with the AI agent.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_agent() -> WeatherAgent:
    try:
        return get_weather_agent()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to init WeatherAgent: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to initialize WeatherAgent.",
        ) from exc


@app.get(
    "/health",
    response_model=HealthResponse,
    dependencies=[Depends(verify_bearer_token)],
    summary="Health check endpoint",
)
async def health_check() -> HealthResponse:
    return HealthResponse()


@app.get(
    "/api/weather/latest",
    response_model=WeatherLatestResponse,
    dependencies=[Depends(verify_bearer_token)],
    summary="Fetch latest weather observation for a city",
)
async def weather_latest(city: str = Query(..., min_length=2)) -> WeatherLatestResponse:
    record = await run_in_threadpool(get_latest_weather, city)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No weather data found for city '{city}'.",
        )

    return WeatherLatestResponse(city=city, data=serialize_record(record))


@app.get(
    "/api/weather/history",
    response_model=WeatherHistoryResponse,
    dependencies=[Depends(verify_bearer_token)],
    summary="Fetch weather history for a city",
)
async def weather_history(
    city: str = Query(..., min_length=2),
    days: int = Query(7, ge=1, le=30),
) -> WeatherHistoryResponse:
    records = await run_in_threadpool(get_weather_history, city, days)
    if not records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No weather history found for city '{city}' in the last {days} days.",
        )

    return WeatherHistoryResponse(city=city, days=days, results=serialize_records(records))


@app.post(
    "/api/agent/query",
    response_model=AgentQueryResponse,
    dependencies=[Depends(verify_bearer_token)],
    summary="Ask the Weather AI agent a question",
)
async def agent_query(payload: AgentQueryRequest) -> AgentQueryResponse:
    agent = _require_agent()
    response = await run_in_threadpool(agent.query, payload.query)
    return AgentQueryResponse(query=payload.query, response=response)

