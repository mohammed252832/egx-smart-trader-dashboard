from __future__ import annotations

import math
import time
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import requests

from .base import Quote, QuoteBatch

DEFAULT_HOSTS = ("query1.finance.yahoo.com", "query2.finance.yahoo.com")
CAIRO_TZ = ZoneInfo("Africa/Cairo")
_HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


def _positive(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def _timestamp(value: Any) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).astimezone(CAIRO_TZ)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _at(values: Any, index: int) -> Any:
    return values[index] if isinstance(values, list) and index < len(values) else None


class YahooQuoteProvider:
    """Low-volume daily-bar fallback when delayed intraday sources are unavailable."""

    name = "yahoo_delayed"

    def __init__(
        self,
        hosts: tuple[str, ...] = DEFAULT_HOSTS,
        timeout: int = 20,
        delay: float = 1.0,
    ) -> None:
        self.hosts = hosts or DEFAULT_HOSTS
        self.timeout = timeout
        self.delay = max(0.0, delay)
        self.session = requests.Session()

    def fetch_quotes(self, symbols: tuple[str, ...]) -> QuoteBatch:
        requested = tuple(dict.fromkeys(symbol.strip().upper().removesuffix(".CA") for symbol in symbols if symbol.strip()))
        if not requested:
            raise RuntimeError("No symbols requested for Yahoo quotes")

        quotes: list[Quote] = []
        errors: list[str] = []
        for symbol in requested:
            last_error = "no Yahoo hosts configured"
            for host in self.hosts:
                try:
                    response = self.session.get(
                        f"https://{host}/v8/finance/chart/{symbol}.CA",
                        params={"range": "5d", "interval": "1d"},
                        headers=_HEADERS,
                        timeout=self.timeout,
                    )
                    if response.status_code == 429:
                        last_error = "rate limit (429)"
                        continue
                    response.raise_for_status()
                    payload = response.json()
                    chart = payload.get("chart") or {}
                    if chart.get("error"):
                        raise RuntimeError(str(chart["error"]))
                    results = chart.get("result") or []
                    if not results:
                        raise RuntimeError("no chart result")
                    quote = self._parse_symbol(symbol, results[0])
                    if quote is None:
                        raise RuntimeError("no usable daily bar")
                    quotes.append(quote)
                    last_error = ""
                    break
                except Exception as exc:
                    last_error = f"{host}: {exc}"
            if last_error:
                errors.append(f"Yahoo {symbol}: {last_error}")
            if self.delay:
                time.sleep(self.delay)

        if not quotes:
            raise RuntimeError("; ".join(errors[:3]) or "Yahoo returned no usable quotes")
        timestamps = [quote.source_timestamp for quote in quotes if quote.source_timestamp]
        return QuoteBatch(
            source=self.name,
            quotes=tuple(quotes),
            source_timestamp=max(timestamps) if timestamps else None,
            delay_seconds=86_400,
            errors=tuple(errors),
        )

    @staticmethod
    def _parse_symbol(symbol: str, result: dict[str, Any]) -> Quote | None:
        timestamps = result.get("timestamp") or []
        values = (result.get("indicators", {}).get("quote") or [{}])[0]
        closes = values.get("close") or []
        valid = [
            (index, float(close))
            for index, close in enumerate(closes)
            if index < len(timestamps) and _positive(close) is not None
        ]
        if not valid:
            return None
        index, price = valid[-1]
        previous_close = valid[-2][1] if len(valid) > 1 else None
        raw_volume = _at(values.get("volume"), index)
        try:
            volume_value = max(0, int(raw_volume or 0))
        except (TypeError, ValueError):
            volume_value = 0
        meta = result.get("meta") or {}
        name = meta.get("longName") or meta.get("shortName")
        return Quote(
            symbol=symbol,
            name=str(name) if name else None,
            price=price,
            previous_close=previous_close,
            change_pct=(price / previous_close - 1) * 100 if previous_close else None,
            open=_positive(_at(values.get("open"), index)),
            high=_positive(_at(values.get("high"), index)),
            low=_positive(_at(values.get("low"), index)),
            volume=volume_value,
            turnover=None,
            source_timestamp=_timestamp(timestamps[index]),
        )
