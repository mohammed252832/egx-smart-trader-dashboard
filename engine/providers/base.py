from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class UniverseEntry:
    symbol: str
    name: str
    sector: str | None = None


@dataclass(frozen=True)
class Bar:
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int = 0


@dataclass(frozen=True)
class Quote:
    symbol: str
    name: str | None
    price: float
    previous_close: float | None
    change_pct: float | None
    open: float | None
    high: float | None
    low: float | None
    volume: int
    turnover: float | None
    source_timestamp: datetime | None


@dataclass(frozen=True)
class QuoteBatch:
    source: str
    quotes: tuple[Quote, ...]
    source_timestamp: datetime | None
    delay_seconds: int
    errors: tuple[str, ...] = ()


class Provider(ABC):
    """Common interface for every market-data source."""

    name: str = "base"
    last_error: str | None = None

    # Quote-only sources (e.g. Borsa) have no trading date of their own. The
    # aggregator binds one from a history provider before collecting their bars.
    needs_trade_date: bool = False

    @abstractmethod
    def fetch_universe(self) -> list[UniverseEntry]:
        """Return all symbols available from this source."""

    @abstractmethod
    def fetch_history(self, symbol: str, days: int) -> list[Bar]:
        """Return the last `days` daily bars for one symbol."""

    def bind_trade_date(self, trade_date: date) -> None:
        """Optional hook for quote-only providers; default is a no-op."""
