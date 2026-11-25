from __future__ import annotations

from datetime import date
from typing import Any

import requests

from .base import Bar, Provider, UniverseEntry

DEFAULT_BASE_URL = "https://demo.borsa.ashh.me"

_HEADERS = {
    "User-Agent": "EGX-Smart-Trader/1.0 (+Borsa integration)",
    "Accept": "application/json",
}


def _positive_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _normalise(symbol: Any) -> str:
    return str(symbol or "").strip().upper().removesuffix(".CA")


class BorsaProvider(Provider):
    """Open-source Borsa API: unified EGX universe + latest normalised quotes.

    Borsa has no history endpoint; its quotes are cached Yahoo Finance values.
    We therefore use it as a universe/sector source and as a same-day price
    confirmation, and let the aggregator supply the real trading date.
    """

    name = "borsa"
    needs_trade_date = True

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str = "",
        symbols: tuple[str, ...] = (),
        timeout: int = 20,
    ) -> None:
        self.base_url = (base_url or DEFAULT_BASE_URL).strip().rstrip("/")
        self.api_key = (api_key or "").strip()
        # Only track symbols we can back with daily history, so the broader
        # Borsa catalogue does not introduce single-bar stocks into the model.
        self.symbols = tuple(_normalise(s) for s in symbols if _normalise(s))
        if not self.symbols:
            raise RuntimeError("BorsaProvider requires an explicit symbol list from the universe config")
        self.timeout = timeout
        self.trade_date: date | None = None
        self._quotes: dict[str, dict[str, Any]] | None = None
        self.last_error = None

    def bind_trade_date(self, trade_date: date) -> None:
        self.trade_date = trade_date

    def _get(self, path: str) -> Any:
        headers = dict(_HEADERS)
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        response = requests.get(
            f"{self.base_url}{path}",
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def fetch_universe(self) -> list[UniverseEntry]:
        payload = self._get("/v1/stocks")
        items = payload.get("symbols", []) if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            raise RuntimeError("Borsa /v1/stocks response is not a list")

        allowed = set(self.symbols)
        entries: list[UniverseEntry] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            symbol = _normalise(item.get("symbol"))
            if symbol not in allowed:
                continue
            sector = item.get("sector")
            sector = None if sector in (None, "", "Unknown") else str(sector)
            name = str(item.get("name") or symbol)
            entries.append(UniverseEntry(symbol=symbol, name=name, sector=sector))

        if not entries:
            raise RuntimeError("No Borsa symbols matched the configured universe list")
        priority = {symbol: index for index, symbol in enumerate(self.symbols)}
        entries.sort(key=lambda entry: (priority.get(entry.symbol, 10_000), entry.symbol))
        self.last_error = None
        return entries

    def fetch_history(self, symbol: str, days: int) -> list[Bar]:
        if self.trade_date is None:
            # The aggregator calls bind_trade_date() from a real history source
            # first; never guess a date from Borsa's fetch-time timestamp.
            self.last_error = "trade date not bound to a history provider"
            return []

        if self._quotes is None:
            try:
                payload = self._get("/v1/quotes")
                rows = payload if isinstance(payload, list) else []
                self._quotes = {
                    _normalise(row.get("symbol")): row for row in rows if isinstance(row, dict)
                }
            except Exception as exc:
                self._quotes = {}
                self.last_error = f"quotes: {exc}"
                return []

        quote = self._quotes.get(_normalise(symbol))
        if not quote:
            return []

        close = _positive_float(quote.get("price"))
        if close is None:
            return []
        high = _positive_float(quote.get("high")) or close
        low = _positive_float(quote.get("low")) or close

        # Volume stays at zero: Borsa's quote is sourced from the same Yahoo bar
        # we already aggregate, so adding it would double-count daily volume.
        self.last_error = None
        return [
            Bar(
                trade_date=self.trade_date,
                open=close,
                high=max(close, high),
                low=min(close, low),
                close=close,
                volume=0,
            )
        ]
