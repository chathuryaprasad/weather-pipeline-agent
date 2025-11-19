"""Utility helpers for serializing database records."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, List


def _serialize_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def serialize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Convert DB record into JSON-serializable dict."""
    if not record:
        return {}

    normalized = record.copy()
    if "city" not in normalized and "city_name" in normalized:
        normalized["city"] = normalized["city_name"]

    return {
        key: _serialize_value(value)
        for key, value in normalized.items()
        if value is not None
    }


def serialize_records(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [serialize_record(record) for record in records]

