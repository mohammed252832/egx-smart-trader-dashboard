from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import requests

from .base import Quote, QuoteBatch

DEFAULT_BASE_URL = "https://ticker.egidegypt.com"
DEFAULT_PUBLIC_TICKER_URL = "https://feed.egitdns.net/api/DelayedFeed/getTickerInfo"
CAIRO_TZ = ZoneInfo("Africa/Cairo")
_KEY_RE = re.compile(r"[^a-z0-9]+")
_TIME_RE = re.compile(r"^\d{1,2}:\d{2}(?::\d{2})?$")
_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
}


def _key(value: Any) -> str:
    return _KEY_RE.sub("", str(value).lower())


def _pick(row: dict[str, Any], *names: str) -> Any:
    values = {_key(key): value for key, value in row.items()}
    for name in names:
        value = values.get(_key(name))
        if value not in (None, ""):
            return value
    return None


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(str(value).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _positive(value: Any) -> float | None:
    number = _number(value)
    return number if number is not None and number > 0 else None


def _symbol(value: Any) -> str:
    symbol = str(value or "").strip().upper().removesuffix(".CA")
    return symbol if symbol.isalnum() else ""


def _timestamp(value: Any, now: datetime) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)) or str(value).strip().replace(".", "", 1).isdigit():
        try:
            seconds = float(value)
            if seconds > 1_000_000_000_000:
                seconds /= 1000
            return datetime.fromtimestamp(seconds, tz=timezone.utc).astimezone(CAIRO_TZ)
        except (TypeError, ValueError, OverflowError, OSError):
            return None

    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        parsed = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%m/%d/%Y %I:%M:%S %p", "%d/%m/%Y %H:%M:%S"):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
    if parsed is None and _TIME_RE.match(text):
        try:
            clock = datetime.strptime(text, "%H:%M:%S" if text.count(":") == 2 else "%H:%M").time()
            parsed = datetime.combine(now.date(), clock)
        except ValueError:
            return None
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=CAIRO_TZ)
    return parsed.astimezone(CAIRO_TZ)


def _rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []
    if any(_key(key) in {"symbol", "symbolcode", "reuters", "ticker"} for key in payload):
        return [payload]
    for key in ("data", "result", "items", "marketWatch", "quotes", "rows"):
        if key in payload:
            found = _rows(payload[key])
            if found:
                return found
    for value in payload.values():
        found = _rows(value)
        if found:
            return found
    return []


def _token(payload: Any) -> str | None:
    if isinstance(payload, str) and payload.strip():
        return payload.strip()
    if not isinstance(payload, dict):
        return None
    for key in ("token", "accessToken", "access_token", "jwt", "value", "result"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for key in ("data", "result"):
        found = _token(payload.get(key))
        if found:
            return found
    return None


def _parse_quotes(
    payload: Any,
    symbols: tuple[str, ...] | None,
    now: datetime,
) -> tuple[Quote, ...]:
    quotes: list[Quote] = []
    for row in _rows(payload):
        symbol = _symbol(_pick(row, "symbol", "symbolCode", "reuters", "ticker", "code"))
        price = _positive(
            _pick(
                row,
                "lastTradePrice",
                "lastPrice",
                "last",
                "price",
                "closePrice",
                "close",
                "currentPrice",
                "marketPrice",
            )
        )
        if not symbol or price is None:
            continue
        previous_close = _positive(
            _pick(row, "previousClose", "prevClose", "lastClose", "previousClosingPrice")
        )
        change_pct = _number(
            _pick(row, "lastChangePrc", "changePct", "changePercent", "changePercentage")
        )
        if change_pct is None and previous_close:
            change_pct = (price / previous_close - 1) * 100
        raw_timestamp = _pick(
            row,
            "lastTradeDate",
            "lastUpdate",
            "lastUpdated",
            "timestamp",
            "lastTradeTime",
            "updateTime",
            "dateTime",
        )
        if raw_timestamp is None:
            raw_date = _pick(row, "date", "tradeDate")
            raw_time = _pick(row, "time", "tradeTime")
            if raw_date not in (None, "") and raw_time not in (None, ""):
                raw_timestamp = f"{raw_date} {raw_time}"
        open_ = _positive(_pick(row, "open", "openPrice"))
        high = _positive(_pick(row, "high", "highPrice"))
        low = _positive(_pick(row, "low", "lowPrice"))
        volume = max(0, int(_number(_pick(row, "totalVolume", "volume", "quantity")) or 0))
        name_value = _pick(
            row,
            "engShortname",
            "engName",
            "englishName",
            "name",
            "companyName",
            "arbShortname",
            "arbName",
            "arabicName",
        )
        quotes.append(
            Quote(
                symbol=symbol,
                name=str(name_value).strip() if name_value not in (None, "") else None,
                price=price,
                previous_close=previous_close,
                change_pct=change_pct,
                open=open_,
                high=max(high, price) if high is not None else None,
                low=min(low, price) if low is not None else None,
                volume=volume,
                turnover=_positive(
                    _pick(row, "totalValue", "turnover", "value", "tradedValue")
                ),
                source_timestamp=_timestamp(raw_timestamp, now),
            )
        )
    if symbols is not None:
        wanted = {
            symbol.strip().upper().removesuffix(".CA")
            for symbol in symbols
            if symbol.strip()
        }
        quotes = [quote for quote in quotes if quote.symbol in wanted]
    return tuple(quotes)


def _quote_batch(source: str, quotes: tuple[Quote, ...], delay_seconds: int) -> QuoteBatch:
    if not quotes:
        raise RuntimeError(f"{source} returned no usable quotes")
    timestamps = [quote.source_timestamp for quote in quotes if quote.source_timestamp]
    return QuoteBatch(
        source=source,
        quotes=quotes,
        source_timestamp=max(timestamps) if timestamps else None,
        delay_seconds=delay_seconds,
    )


class EgidQuoteProvider:
    """Authenticated client for the official EGID delayed market feed."""

    name = "egid_delayed"

    def __init__(
        self,
        username: str,
        password: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 20,
        delay_seconds: int = 900,
    ) -> None:
        self.username = username.strip()
        self.password = password
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.delay_seconds = max(0, delay_seconds)
        self.session = requests.Session()
        self._access_token: str | None = None

    def _get_token(self) -> str:
        if not self.username or not self.password:
            raise RuntimeError("EGID_USERNAME and EGID_PASSWORD are required")
        response = self.session.post(
            f"{self.base_url}/api/Settings/GetToken",
            json={"Username": self.username, "Password": self.password},
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        if not response.ok:
            raise RuntimeError(f"EGID token request failed ({response.status_code})")
        try:
            access_token = _token(response.json())
        except ValueError as exc:
            raise RuntimeError("EGID token response was not valid JSON") from exc
        if not access_token:
            raise RuntimeError("EGID token response did not contain a token")
        self._access_token = access_token
        return access_token

    def _get(self, path: str) -> Any:
        for attempt in range(2):
            token = self._access_token or self._get_token()
            response = self.session.get(
                f"{self.base_url}{path}",
                headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
                timeout=self.timeout,
            )
            if response.status_code == 401 and attempt == 0:
                self._access_token = None
                continue
            if not response.ok:
                raise RuntimeError(f"EGID {path} failed ({response.status_code})")
            try:
                return response.json()
            except ValueError as exc:
                raise RuntimeError(f"EGID {path} returned invalid JSON") from exc
        raise RuntimeError(f"EGID {path} failed after token refresh")

    def fetch_quotes(self, symbols: tuple[str, ...] | None = None) -> QuoteBatch:
        payload = self._get("/api/DelayedFeed/getAllMarketWatch")
        quotes = _parse_quotes(payload, symbols, datetime.now(CAIRO_TZ))
        return _quote_batch(self.name, quotes, self.delay_seconds)


class EgidPublicQuoteProvider:
    """Credential-free client for the official EGID website ticker."""

    name = "egid_public_delayed"

    def __init__(
        self,
        ticker_url: str = DEFAULT_PUBLIC_TICKER_URL,
        timeout: int = 20,
        delay_seconds: int = 900,
    ) -> None:
        self.ticker_url = ticker_url
        self.timeout = timeout
        self.delay_seconds = max(0, delay_seconds)

    def fetch_quotes(self, symbols: tuple[str, ...] | None = None) -> QuoteBatch:
        response = requests.get(self.ticker_url, headers=_HEADERS, timeout=self.timeout)
        if not response.ok:
            raise RuntimeError(f"EGID public ticker failed ({response.status_code})")
        try:
            payload = response.json()
        except ValueError as exc:
            raise RuntimeError("EGID public ticker returned invalid JSON") from exc
        quotes = _parse_quotes(payload, symbols, datetime.now(CAIRO_TZ))
        return _quote_batch(self.name, quotes, self.delay_seconds)
