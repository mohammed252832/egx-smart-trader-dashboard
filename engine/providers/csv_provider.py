from __future__ import annotations

import csv
import os
from pathlib import Path

from .base import Bar, Provider, UniverseEntry
from .http_provider import _parse_date, _to_float


class CsvProvider(Provider):
    """Optional local-file source: one universe CSV plus one <SYMBOL>.csv per stock."""

    name = "csv"

    def __init__(self, universe_path: str = "", history_dir: str = ""):
        self._universe_configured = bool(universe_path.strip())
        self._history_configured = bool(history_dir.strip())
        self.universe_path = Path(universe_path) if self._universe_configured else Path("")
        self.history_dir = Path(history_dir) if self._history_configured else Path("")
        self.last_error = None

    @property
    def enabled(self) -> bool:
        return (
            self._universe_configured
            and self._history_configured
            and self.universe_path.is_file()
            and self.history_dir.is_dir()
        )

    @classmethod
    def from_env(cls) -> "CsvProvider":
        return cls(
            universe_path=os.getenv("EGX_UNIVERSE_CSV", "").strip(),
            history_dir=os.getenv("EGX_HISTORY_DIR", "").strip(),
        )

    def fetch_universe(self) -> list[UniverseEntry]:
        if not self.enabled:
            return []
        with open(self.universe_path, encoding="utf-8-sig", newline="") as handle:
            return [
                UniverseEntry(
                    symbol=row["symbol"].strip().upper(),
                    name=(row.get("name") or row["symbol"]).strip(),
                    sector=(row.get("sector") or "").strip() or None,
                )
                for row in csv.DictReader(handle)
                if row.get("symbol", "").strip()
            ]

    def fetch_history(self, symbol: str, days: int) -> list[Bar]:
        if not self.enabled:
            return []
        path = self.history_dir / f"{symbol}.csv"
        if not path.exists():
            path = self.history_dir / f"{symbol.lower()}.csv"
        if not path.exists():
            return []

        bars: list[Bar] = []
        with open(path, encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                trade_date = _parse_date(row.get("date") or row.get("trade_date"))
                close = _to_float(row.get("close"))
                if trade_date is None or close is None:
                    continue
                open_price = _to_float(row.get("open")) or close
                high = _to_float(row.get("high")) or max(open_price, close)
                low = _to_float(row.get("low")) or min(open_price, close)
                bars.append(
                    Bar(
                        trade_date=trade_date,
                        open=open_price,
                        high=max(high, open_price, close),
                        low=min(low, open_price, close),
                        close=close,
                        volume=int(_to_float(row.get("volume")) or 0),
                    )
                )
        bars.sort(key=lambda bar: bar.trade_date)
        return bars[-days:] if days > 0 else bars
