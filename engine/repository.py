from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any, Iterable

import requests


def _serialize(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, float) and (not math.isfinite(value)):
        return None
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    return value


def _chunks(rows: list[dict[str, Any]], size: int = 200) -> Iterable[list[dict[str, Any]]]:
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


class SupabaseRepository:
    """Thin PostgREST client for the engine (service-role key only)."""

    def __init__(self, url: str, service_role_key: str, timeout: int = 20):
        self.base_url = f"{url.rstrip('/')}/rest/v1"
        self.timeout = timeout
        self.headers = {
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request(
        self,
        method: str,
        table: str,
        *,
        params: dict[str, Any] | None = None,
        payload: Any = None,
        prefer: str = "return=minimal",
    ) -> Any:
        headers = dict(self.headers)
        headers["Prefer"] = prefer
        response = requests.request(
            method,
            f"{self.base_url}/{table}",
            headers=headers,
            params=params,
            json=_serialize(payload) if payload is not None else None,
            timeout=self.timeout,
        )
        if not response.ok:
            raise RuntimeError(f"{method} {table} failed ({response.status_code}): {response.text[:400]}")
        if not response.text.strip():
            return None
        return response.json()

    def select(self, table: str, columns: str = "*", params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        query = {"select": columns, **(params or {})}
        return self._request("GET", table, params=query) or []

    def insert(self, table: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            return []
        result = self._request("POST", table, payload=rows, prefer="return=representation")
        return result if isinstance(result, list) else []

    def upsert(self, table: str, rows: list[dict[str, Any]], on_conflict: str) -> None:
        for chunk in _chunks(rows):
            self._request(
                "POST",
                table,
                params={"on_conflict": on_conflict},
                payload=chunk,
                prefer="resolution=merge-duplicates,return=minimal",
            )

    def update(self, table: str, payload: dict[str, Any], params: dict[str, Any] | None = None) -> None:
        self._request("PATCH", table, params=params, payload=payload)
