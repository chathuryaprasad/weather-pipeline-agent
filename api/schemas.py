"""Pydantic schemas for API payloads."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentQueryRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Natural language weather question")


class AgentQueryResponse(BaseModel):
    query: str
    response: str


class WeatherLatestResponse(BaseModel):
    city: str
    data: Dict[str, Any]


class WeatherHistoryResponse(BaseModel):
    city: str
    days: int
    results: List[Dict[str, Any]]


class HealthResponse(BaseModel):
    status: str = "ok"

