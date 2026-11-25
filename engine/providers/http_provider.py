from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import requests

from ..config import ProviderConfig
from .base import Bar, Provider, UniverseEntry

_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y-%m-%dT%H:%M:%S")
_LIST_KEYS = ("data", "results", "items", "rows", "bars", "history", "prices", "symbols", "stocks")


def _render(template: str, values: dict[str, Any]) -> str:
    """Replace supported placeholders without failing on unrelated braces."""
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", str(value))
    return rendered


def _find_records(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in _LIST_KEYS:
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            nested = _find_records(value)
            if nested:
                return nested
    if payload and all(isinstance(value, (dict, list)) for value in payload.values()):
        records: list[Any] = []
        for key, value in payload.items():
            if isinstance(value, dict):
                record = dict(value)
                record.setdefault("symbol", key)
                records.append(record)
        if records:
            return records
    return []


def _pick(record: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return None


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        seconds = float(value) / 1000 if float(value) > 1e11 else float(value)
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc).date()
        except (OSError, OverflowError, ValueError):
            return None
    text = str(value).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text[:19], fmt).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result and abs(result) != float("inf") else None


class HttpProvider(Provider):
    """Generic, env-driven REST adapter for licensed EGX data vendors."""

    def __init__(self, config: ProviderConfig, timeout: int = 20):
        self.config = config
        # Prefix the name so a generic BORSA_* template cannot overwrite the
        # dedicated BorsaProvider entry in collected.raw_bars/source_rows.
        self.name = f"http_{config.prefix.lower()}"
        self.timeout = timeout
        self.last_error = None

    def _get(self, template: str, **values: Any) -> Any:
        url = _render(template, values)
        headers: dict[str, str] = {"Accept": "application/json"}
        headers.update(self.config.extra_headers)
        if self.config.api_key:
            configured = self.config.auth_header
            if configured and "{token}" in configured:
                header_name, header_value = configured.split(":", 1) if ":" in configured else (configured, "{token}")
                headers[header_name.strip()] = header_value.replace("{token}", self.config.api_key).strip()
            elif configured:
                headers[configured] = self.config.api_key
            else:
                # Both headers keep the generic adapter compatible with vendors
                # that use Bearer tokens and vendors that expect X-API-Key.
                headers["Authorization"] = f"Bearer {self.config.api_key}"
                headers["x-api-key"] = self.config.api_key
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def fetch_universe(self) -> list[UniverseEntry]:
        self.last_error = None
        if not self.config.universe_url:
            return []
        try:
            payload = self._get(self.config.universe_url)
        except Exception as exc:  # network/parse failures are reported, not fatal
            self.last_error = f"universe: {exc}"
            return []

        entries: list[UniverseEntry] = []
        for record in _find_records(payload):
            if isinstance(record, str):
                symbol, name, sector = record.strip().upper(), record.strip(), None
            elif isinstance(record, dict):
                raw_symbol = _pick(record, ("symbol", "ticker", "code", "ticker_symbol", "Symbol"))
                if not raw_symbol:
                    continue
                symbol = str(raw_symbol).strip().upper()
                name = str(
                    _pick(
                        record,
                        ("name", "company_name", "companyName", "name_ar", "nameAr", "security_name", "description"),
                    )
                    or symbol
                )
                sector_value = _pick(record, ("sector", "industry", "sector_name"))
                sector = str(sector_value) if sector_value else None
            else:
                continue
            if symbol:
                entries.append(UniverseEntry(symbol=symbol, name=name, sector=sector))
        return entries

    def fetch_history(self, symbol: str, days: int) -> list[Bar]:
        if not self.config.history_url:
            return []
        end = date.today()
        start = end - timedelta(days=max(1, days))
        try:
            payload = self._get(
                self.config.history_url,
                symbol=symbol,
                days=days,
                api_key=self.config.api_key,
                start=start.isoformat(),
                end=end.isoformat(),
            )
        except Exception as exc:
            self.last_error = f"history[{symbol}]: {exc}"
            return []

        bars: list[Bar] = []
        for record in _find_records(payload):
            if not isinstance(record, dict):
                continue
            trade_date = _parse_date(
                _pick(record, ("trade_date", "date", "time", "timestamp", "datetime", "Date"))
            )
            close = _to_float(_pick(record, ("close", "price", "last", "last_price", "Close")))
            if trade_date is None or close is None or close <= 0:
                continue
            open_price = _to_float(_pick(record, ("open", "open_price", "Open"))) or close
            high = _to_float(_pick(record, ("high", "high_price", "High"))) or max(open_price, close)
            low = _to_float(_pick(record, ("low", "low_price", "Low"))) or min(open_price, close)
            volume = _to_float(_pick(record, ("volume", "vol", "Volume"))) or 0
            high = max(high, open_price, close)
            low = min(low, open_price, close)
            bars.append(
                Bar(
                    trade_date=trade_date,
                    open=round(open_price, 4),
                    high=round(high, 4),
                    low=round(low, 4),
                    close=round(close, 4),
                    volume=int(volume),
                )
            )
        bars.sort(key=lambda bar: bar.trade_date)
        return bars
