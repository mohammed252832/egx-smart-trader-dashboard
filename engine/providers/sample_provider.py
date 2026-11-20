from __future__ import annotations

import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path

from .base import Bar, Provider, UniverseEntry

_UNIVERSE_PATH = Path(__file__).resolve().parent.parent / "sample_data" / "universe.csv"


def _business_days(count: int, end: date | None = None) -> list[date]:
    """EGX trades Sunday to Thursday."""
    cursor = end or date.today()
    result: list[date] = []
    while len(result) < count:
        if cursor.weekday() in {6, 0, 1, 2, 3}:
            result.append(cursor)
        cursor -= timedelta(days=1)
    result.reverse()
    return result


class SampleProvider(Provider):
    """Deterministic synthetic market data so the pipeline runs without API keys."""

    name = "sample"

    def __init__(self, days: int = 400, universe_path: Path = _UNIVERSE_PATH):
        self.days = days
        self.universe_path = universe_path
        self.last_error = None

    def fetch_universe(self) -> list[UniverseEntry]:
        with open(self.universe_path, encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            return [
                UniverseEntry(
                    symbol=row["symbol"].strip().upper(),
                    name=row.get("name", "").strip() or row["symbol"].strip(),
                    sector=(row.get("sector") or "").strip() or None,
                )
                for row in reader
                if row.get("symbol", "").strip()
            ]

    def fetch_history(self, symbol: str, days: int) -> list[Bar]:
        count = max(days, self.days)
        seed = sum(ord(char) for char in symbol.upper())
        rng = random.Random(f"{symbol}:{count}")
        base_price = 5 + (seed % 120)
        volatility = 0.012 + (seed % 7) * 0.002
        drift = 0.0002 + ((seed % 5) - 2) * 0.0003
        phase = (seed % 100) / 100 * math.tau

        bars: list[Bar] = []
        previous = float(base_price)
        for index, trade_date in enumerate(_business_days(count)):
            regime = math.sin(index / 11 + phase) * 0.0035
            change = max(-0.09, min(0.09, drift + regime + rng.gauss(0, volatility)))
            close = max(0.5, previous * (1 + change))
            open_price = max(0.5, previous * (1 + rng.gauss(0, volatility * 0.35)))
            high = max(open_price, close) * (1 + abs(rng.gauss(0, volatility * 0.45)))
            low = min(open_price, close) * (1 - abs(rng.gauss(0, volatility * 0.45)))
            volume = int((200_000 + base_price * 4_000) * (1 + abs(change) * 30) * rng.uniform(0.6, 1.5))

            bars.append(
                Bar(
                    trade_date=trade_date,
                    open=round(open_price, 2),
                    high=round(high, 2),
                    low=round(low, 2),
                    close=round(close, 2),
                    volume=volume,
                )
            )
            previous = close

        return bars
