from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import requests

from .base import Quote, QuoteBatch

DEFAULT_SCANNER_URL = "https://scanner.tradingview.com/egypt/scan"
CAIRO_TZ = ZoneInfo("Africa/Cairo")
COLUMNS = [
    "name",
    "close",
    "change",
    "change_abs",
    "volume",
    "high",
    "low",
    "open",
    "previous_close",
    "update_time",
]


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _positive(value: Any) -> float | None:
    number = _number(value)
    return number if number is not None and number > 0 else None


def _symbol(value: Any) -> str:
    symbol = str(value or "").strip().upper().split(":")[-1].removesuffix(".CA")
    return symbol if symbol.isalnum() else ""


def _timestamp(value: Any) -> datetime | None:
    seconds = _number(value)
    if seconds is None or seconds <= 0:
        return None
    try:
        return datetime.fromtimestamp(seconds, tz=timezone.utc).astimezone(CAIRO_TZ)
    except (OverflowError, OSError, ValueError):
        return None


class TradingViewQuoteProvider:
    """Bulk delayed EGX quotes from TradingView's public scanner endpoint."""

    name = "tradingview_delayed"

    def __init__(
        self,
        scanner_url: str = DEFAULT_SCANNER_URL,
        timeout: int = 20,
        delay_seconds: int = 900,
        chunk_size: int = 100,
    ) -> None:
        self.scanner_url = scanner_url
        self.timeout = timeout
        self.delay_seconds = max(0, delay_seconds)
        self.chunk_size = max(1, min(200, chunk_size))
        self.session = requests.Session()

    def fetch_quotes(self, symbols: tuple[str, ...]) -> QuoteBatch:
        requested = tuple(dict.fromkeys(symbol.strip().upper().removesuffix(".CA") for symbol in symbols if symbol.strip()))
        if not requested:
            raise RuntimeError("No symbols requested for TradingView quotes")

        quotes: list[Quote] = []
        errors: list[str] = []
        for start in range(0, len(requested), self.chunk_size):
            chunk = requested[start : start + self.chunk_size]
            response = self.session.post(
                self.scanner_url,
                json={
                    "symbols": {"tickers": [f"EGX:{symbol}" for symbol in chunk]},
                    "columns": COLUMNS,
                },
                headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"},
                timeout=self.timeout,
            )
            if not response.ok:
                raise RuntimeError(f"TradingView scanner failed ({response.status_code})")
            try:
                payload = response.json()
            except ValueError as exc:
                raise RuntimeError("TradingView scanner returned invalid JSON") from exc
            rows = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(rows, list):
                raise RuntimeError("TradingView scanner response did not contain quote rows")

            returned: set[str] = set()
            for row in rows:
                if not isinstance(row, dict):
                    continue
                symbol = _symbol(row.get("s"))
                values = row.get("d")
                if not symbol or not isinstance(values, list):
                    continue
                data = dict(zip(COLUMNS, values))
                price = _positive(data.get("close"))
                if price is None:
                    continue
                returned.add(symbol)
                change_abs = _number(data.get("change_abs"))
                previous_close = _positive(data.get("previous_close"))
                if previous_close is None and change_abs is not None:
                    candidate = price - change_abs
                    previous_close = candidate if candidate > 0 else None
                change_pct = _number(data.get("change"))
                if change_pct is None and previous_close:
                    change_pct = (price / previous_close - 1) * 100
                high = _positive(data.get("high"))
                low = _positive(data.get("low"))
                volume = max(0, int(_number(data.get("volume")) or 0))
                name = data.get("name")
                quotes.append(
                    Quote(
                        symbol=symbol,
                        name=str(name).strip() if name not in (None, "") else None,
                        price=price,
                        previous_close=previous_close,
                        change_pct=change_pct,
                        open=_positive(data.get("open")),
                        high=max(high, price) if high is not None else None,
                        low=min(low, price) if low is not None else None,
                        volume=volume,
                        turnover=None,
                        source_timestamp=_timestamp(data.get("update_time")),
                    )
                )
            missing = [symbol for symbol in chunk if symbol not in returned]
            if missing:
                errors.append(f"TradingView missing {len(missing)} symbol(s): {', '.join(missing[:5])}")

        if not quotes:
            raise RuntimeError("TradingView scanner returned no usable EGX quotes")
        timestamps = [quote.source_timestamp for quote in quotes if quote.source_timestamp]
        return QuoteBatch(
            source=self.name,
            quotes=tuple(quotes),
            source_timestamp=max(timestamps) if timestamps else None,
            delay_seconds=self.delay_seconds,
            errors=tuple(errors),
        )
