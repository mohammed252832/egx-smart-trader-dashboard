from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import patch

import pandas as pd

from engine import run as run_module


class FakeRepository:
    def __init__(self) -> None:
        self.upserts: list[tuple[str, list[dict], str]] = []
        self.updates: list[tuple[dict, dict]] = []

    def insert(self, table: str, rows: list[dict]) -> list[dict]:
        return [{"id": "run-1", **rows[0]}]

    def select(self, table: str, columns: str = "*", params: dict | None = None) -> list[dict]:
        return [{"market_date": "2026-11-25", "notes": ""}]

    def upsert(self, table: str, rows: list[dict], on_conflict: str) -> None:
        self.upserts.append((table, rows, on_conflict))

    def update(self, table: str, payload: dict, params: dict | None = None) -> None:
        self.updates.append((payload, params or {}))


class RunTests(TestCase):
    def test_skipped_session_still_persists_expanded_market_history(self) -> None:
        dates = pd.bdate_range("2026-10-01", periods=40)
        frame = pd.DataFrame(
            {
                "trade_date": dates,
                "open": 20.0,
                "high": 21.0,
                "low": 19.0,
                "close": 20.5,
                "volume": 1000,
            }
        )
        quality = SimpleNamespace(
            kept_rows=40,
            raw_rows=40,
            invalid_prices=0,
            invalid_ohlc=0,
            impossible_jumps=0,
            extreme_ranges=0,
            as_dict=lambda: {},
        )
        collected = SimpleNamespace(
            universe={"NEW": SimpleNamespace(symbol="NEW", name="New Stock", sector="Test")},
            source_rows={"yahoo": 40},
            source_errors={},
            raw_bars={},
        )
        config = SimpleNamespace(
            model_version="test",
            horizon_days=3,
            top_n=10,
            universe=SimpleNamespace(minimum_universe_size=1),
        )
        repo = FakeRepository()

        with (
            patch.object(run_module, "collect", return_value=collected),
            patch.object(run_module, "filter_bars", return_value=({}, quality)),
            patch.object(run_module, "aggregate_bars", return_value={"NEW": frame}),
            patch.object(run_module, "apply_universe_filters", return_value=({"NEW": frame}, {}, [])),
        ):
            result = run_module._run(config, repo)

        self.assertEqual(result, 0)
        price_upserts = [rows for table, rows, _ in repo.upserts if table == "price_bars"]
        self.assertEqual(len(price_upserts), 1)
        self.assertEqual(len(price_upserts[0]), 40)
        self.assertTrue(all(row["symbol"] == "NEW" and row["source"] == "aggregated" for row in price_upserts[0]))
        self.assertEqual(repo.updates[0][0]["status"], "skipped")


if __name__ == "__main__":
    main()
