from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


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


class Provider(ABC):
    """Common interface for every market-data source."""

    name: str = "base"
    last_error: str | None = None

    @abstractmethod
    def fetch_universe(self) -> list[UniverseEntry]:
        """Return all symbols available from this source."""

    @abstractmethod
    def fetch_history(self, symbol: str, days: int) -> list[Bar]:
        """Return the last `days` daily bars for one symbol."""
