from __future__ import annotations

import time
from datetime import date, datetime, timezone
from typing import Any

import requests

from .base import Bar, Provider, UniverseEntry

# EGID publishes the official EGX symbol list here without authentication.
DEFAULT_UNIVERSE_URL = "https://ticker.egidegypt.com/api/Feed/GetAllMarketWatchNames"
DEFAULT_HOSTS = ("query1.finance.yahoo.com", "query2.finance.yahoo.com")

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "application/json",
}


class YahooProvider(Provider):
    """EGID universe + Yahoo Finance daily OHLCV bars for EGX (.CA) symbols."""

    name = "yahoo"

    def __init__(
        self,
        universe_url: str = DEFAULT_UNIVERSE_URL,
        symbols: tuple[str, ...] = (),
        range_: str = "2y",
        hosts: tuple[str, ...] = DEFAULT_HOSTS,
        timeout: int = 20,
        delay: float = 0.2,
    ) -> None:
        self.universe_url = universe_url
        self.symbols = tuple(s.strip().upper() for s in symbols if s.strip())
        if not self.symbols:
            raise RuntimeError("YahooProvider requires an explicit symbol list from the universe config")
        self.range = range_ or "2y"
        self.hosts = tuple(h.strip() for h in hosts if h.strip()) or DEFAULT_HOSTS
        self.timeout = timeout
        self.delay = max(0.0, delay)
        self.last_error = None

    def fetch_universe(self) -> list[UniverseEntry]:
        response = requests.get(self.universe_url, headers=_HEADERS, timeout=self.timeout)
        response.raise_for_status()
        payload: Any = response.json()
        if isinstance(payload, dict):
            payload = payload.get("data") or payload.get("results") or []
        if not isinstance(payload, list):
            raise RuntimeError("EGID universe response is not a list")

        allowed = set(self.symbols)
        entries: list[UniverseEntry] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            reuters = str(item.get("Reuters") or "").strip().upper()
            if not reuters.endswith(".CA"):
                continue
            symbol = reuters[:-3].strip()
            if not symbol.isalnum() or symbol not in allowed:
                continue
            name = (
                item.get("eng_shortname")
                or item.get("ENG_NAME")
                or item.get("ARB_NAME")
                or symbol
            )
            entries.append(UniverseEntry(symbol=symbol, name=str(name)))

        if not entries:
            raise RuntimeError("No EGID symbols matched the configured universe list")

        priority = {symbol: index for index, symbol in enumerate(self.symbols)}
        entries.sort(key=lambda entry: (priority.get(entry.symbol, 10_000), entry.symbol))
        self.last_error = None
        return entries

    def fetch_history(self, symbol: str, days: int) -> list[Bar]:
        ticker = symbol.upper()
        if not ticker.endswith(".CA"):
            ticker = f"{ticker}.CA"

        last_error = "no Yahoo hosts configured"
        for host in self.hosts:
            url = f"https://{host}/v8/finance/chart/{ticker}"
            try:
                response = requests.get(
                    url,
                    params={"range": self.range, "interval": "1d"},
                    headers=_HEADERS,
                    timeout=self.timeout,
                )
                if response.status_code == 429:
                    last_error = "Yahoo rate limit (429)"
                    continue
                response.raise_for_status()
                payload = response.json()
                chart = payload.get("chart") or {}
                if chart.get("error"):
                    raise RuntimeError(str(chart["error"]))
                results = chart.get("result") or []
                if not results:
                    raise RuntimeError("Yahoo returned no chart result")
                bars = self._parse_bars(results[0])
                if not bars:
                    raise RuntimeError("Yahoo returned no usable daily bars")
                self.last_error = None
                if self.delay:
                    time.sleep(self.delay)
                return bars[-max(1, days) :]
            except Exception as exc:
                last_error = f"{host}: {exc}"

        self.last_error = last_error
        raise RuntimeError(last_error)

    @staticmethod
    def _parse_bars(result: dict[str, Any]) -> list[Bar]:
        timestamps = result.get("timestamp") or []
        quotes = (result.get("indicators", {}).get("quote") or [{}])[0]
        opens = quotes.get("open") or []
        highs = quotes.get("high") or []
        lows = quotes.get("low") or []
        closes = quotes.get("close") or []
        volumes = quotes.get("volume") or []

        by_date: dict[date, Bar] = {}
        for index, raw_ts in enumerate(timestamps):
            if index >= len(closes) or index >= len(opens):
                continue
            values = (
                opens[index],
                highs[index] if index < len(highs) else None,
                lows[index] if index < len(lows) else None,
                closes[index],
            )
            if any(value is None for value in values):
                continue  # Yahoo emits a null bar for the in-progress session
            try:
                open_, high, low, close = (float(value) for value in values)
                volume = int(volumes[index] or 0) if index < len(volumes) else 0
                trade_date = datetime.fromtimestamp(int(raw_ts), tz=timezone.utc).date()
            except (TypeError, ValueError, OverflowError, OSError):
                continue
            if close <= 0 or high <= 0 or low <= 0:
                continue
            by_date[trade_date] = Bar(trade_date, open_, high, low, close, volume)

        return [by_date[key] for key in sorted(by_date)]
