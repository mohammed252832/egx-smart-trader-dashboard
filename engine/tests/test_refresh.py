from __future__ import annotations

import os
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from engine.providers.base import Quote, QuoteBatch
from engine.providers.egid_provider import CAIRO_TZ
from engine.refresh import _record_failure, _refresh


class FakeRepository:
    def __init__(self) -> None:
        self.upserts: list[tuple[str, list[dict], str]] = []
        self.recommendations = [{"symbol": "COMI"}, {"symbol": "FWRY"}]

    def select(self, table: str, columns: str = "*", params=None) -> list[dict]:
        if table == "top_recommendations":
            return self.recommendations
        if table == "stocks":
            return [{"symbol": "COMI", "name": "Commercial International Bank"}]
        if table == "data_source_status":
            return [
                {
                    "source": "tradingview_delayed",
                    "last_success_at": "2026-11-24T10:00:00+00:00",
                    "rows_written": 2,
                    "source_timestamp": "2026-11-24T12:00:00+02:00",
                    "delay_seconds": 900,
                    "market_date": "2026-11-24",
                }
            ]
        return []

    def upsert(self, table: str, rows: list[dict], on_conflict: str) -> None:
        self.upserts.append((table, rows, on_conflict))


def make_config(**overrides) -> SimpleNamespace:
    values = {
        "top_n": 2,
        "universe": SimpleNamespace(seed_symbols=("ABUK", "COMI", "FWRY")),
        "egid_enabled": True,
        "egid_username": "",
        "egid_password": "",
        "egid_base_url": "https://ticker.egidegypt.com",
        "egid_delay_seconds": 900,
        "tradingview_enabled": True,
        "tradingview_scanner_url": "https://scanner.tradingview.com/egypt/scan",
        "tradingview_delay_seconds": 900,
        "tradingview_chunk_size": 100,
        "yahoo_quote_enabled": True,
        "yahoo_hosts": ("query1.finance.yahoo.com",),
        "yahoo_quote_delay_seconds": 0,
        "request_timeout": 20,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def make_batch(
    source: str = "tradingview_delayed",
    symbols: tuple[str, ...] = ("COMI", "FWRY"),
    delay_seconds: int = 900,
    errors: tuple[str, ...] = (),
) -> QuoteBatch:
    source_time = datetime(2026, 11, 24, 12, 5, tzinfo=CAIRO_TZ)
    return QuoteBatch(
        source=source,
        quotes=tuple(
            Quote(
                symbol=symbol,
                name=f"{symbol} company",
                price=25.1,
                previous_close=24.9,
                change_pct=0.8032,
                open=25.0,
                high=25.3,
                low=24.8,
                volume=1250,
                turnover=31300,
                source_timestamp=source_time,
            )
            for symbol in symbols
        ),
        source_timestamp=source_time,
        delay_seconds=delay_seconds,
        errors=errors,
    )


def named_provider(name: str, batch: QuoteBatch | None = None, error: Exception | None = None) -> Mock:
    provider = Mock()
    provider.name = name
    if error is not None:
        provider.fetch_quotes.side_effect = error
    else:
        provider.fetch_quotes.return_value = batch
    return provider


class RefreshTests(unittest.TestCase):
    def test_free_mode_uses_tradingview_without_credentials(self) -> None:
        provider = named_provider("tradingview_delayed", make_batch())
        yahoo = named_provider("yahoo_delayed", make_batch("yahoo_delayed", delay_seconds=86_400))
        repo = FakeRepository()

        with patch.dict(os.environ, {"EGX_QUOTE_FORCE_REFRESH": "true"}), patch(
            "engine.refresh.TradingViewQuoteProvider", return_value=provider
        ), patch("engine.refresh.YahooQuoteProvider", return_value=yahoo), patch(
            "engine.refresh.EgidQuoteProvider"
        ) as egid:
            result = _refresh(make_config(), repo)

        self.assertEqual(result, 0)
        egid.assert_not_called()
        provider.fetch_quotes.assert_called_once_with(("COMI", "FWRY"))
        yahoo.fetch_quotes.assert_not_called()
        quote_table = next(item for item in repo.upserts if item[0] == "live_quotes")
        self.assertEqual(quote_table[1][0]["market_date"], "2026-11-24")
        self.assertEqual(quote_table[1][0]["source"], "tradingview_delayed")
        status_table = next(item for item in repo.upserts if item[0] == "data_source_status")
        self.assertEqual(status_table[1][0]["source"], "tradingview_delayed")
        self.assertEqual(status_table[1][0]["rows_written"], 2)
        self.assertEqual(status_table[1][0]["delay_seconds"], 900)

    def test_tradingview_failure_falls_back_to_yahoo_daily_bars(self) -> None:
        tradingview = named_provider("tradingview_delayed", error=RuntimeError("scanner blocked"))
        yahoo = named_provider("yahoo_delayed", make_batch("yahoo_delayed", delay_seconds=86_400))
        repo = FakeRepository()

        with patch.dict(os.environ, {"EGX_QUOTE_FORCE_REFRESH": "true"}), patch(
            "engine.refresh.TradingViewQuoteProvider", return_value=tradingview
        ), patch("engine.refresh.YahooQuoteProvider", return_value=yahoo):
            result = _refresh(make_config(), repo)

        self.assertEqual(result, 0)
        yahoo.fetch_quotes.assert_called_once_with(("COMI", "FWRY"))
        status = next(item for item in repo.upserts if item[0] == "data_source_status")[1][0]
        self.assertEqual(status["source"], "yahoo_delayed")
        self.assertEqual(status["delay_seconds"], 86_400)
        self.assertIn("scanner blocked", status["last_error"])

    def test_egid_has_priority_when_credentials_exist(self) -> None:
        egid = named_provider("egid_delayed", make_batch("egid_delayed"))
        tradingview = named_provider("tradingview_delayed", make_batch())
        repo = FakeRepository()
        config = make_config(egid_username="user", egid_password="secret")

        with patch.dict(os.environ, {"EGX_QUOTE_FORCE_REFRESH": "true"}), patch(
            "engine.refresh.EgidQuoteProvider", return_value=egid
        ), patch("engine.refresh.TradingViewQuoteProvider", return_value=tradingview):
            result = _refresh(config, repo)

        self.assertEqual(result, 0)
        egid.fetch_quotes.assert_called_once_with(("COMI", "FWRY"))
        tradingview.fetch_quotes.assert_not_called()
        status = next(item for item in repo.upserts if item[0] == "data_source_status")[1][0]
        self.assertEqual(status["source"], "egid_delayed")

    def test_partial_quotes_are_kept_and_reported_as_warning(self) -> None:
        batch = make_batch(symbols=("COMI",), errors=("TradingView missing FWRY",))
        provider = named_provider("tradingview_delayed", batch)
        repo = FakeRepository()

        with patch.dict(os.environ, {"EGX_QUOTE_FORCE_REFRESH": "true"}), patch(
            "engine.refresh.TradingViewQuoteProvider", return_value=provider
        ):
            result = _refresh(make_config(), repo)

        self.assertEqual(result, 0)
        status = next(item for item in repo.upserts if item[0] == "data_source_status")[1][0]
        self.assertEqual(status["rows_written"], 1)
        self.assertIn("missing FWRY", status["last_error"])

    def test_seed_symbols_are_used_before_recommendations_exist(self) -> None:
        provider = named_provider("tradingview_delayed", make_batch(symbols=("ABUK", "COMI")))
        repo = FakeRepository()
        repo.recommendations = []

        with patch.dict(os.environ, {"EGX_QUOTE_FORCE_REFRESH": "true"}), patch(
            "engine.refresh.TradingViewQuoteProvider", return_value=provider
        ):
            result = _refresh(make_config(), repo)

        self.assertEqual(result, 0)
        provider.fetch_quotes.assert_called_once_with(("ABUK", "COMI"))

    def test_total_failure_keeps_last_success_timestamp(self) -> None:
        tradingview = named_provider("tradingview_delayed", error=RuntimeError("scanner blocked"))
        yahoo = named_provider("yahoo_delayed", error=RuntimeError("Yahoo unavailable"))
        repo = FakeRepository()

        with patch.dict(os.environ, {"EGX_QUOTE_FORCE_REFRESH": "true"}), patch(
            "engine.refresh.TradingViewQuoteProvider", return_value=tradingview
        ), patch("engine.refresh.YahooQuoteProvider", return_value=yahoo):
            result = _refresh(make_config(), repo)

        self.assertEqual(result, 1)
        self.assertFalse(any(table == "live_quotes" for table, _, _ in repo.upserts))
        status = next(item for item in repo.upserts if item[0] == "data_source_status")[1][0]
        self.assertEqual(status["source"], "tradingview_delayed")
        self.assertEqual(status["last_success_at"], "2026-11-24T10:00:00+00:00")
        self.assertIn("All quote sources failed", status["last_error"])

    def test_failure_status_uses_the_attempted_source(self) -> None:
        repo = FakeRepository()
        _record_failure(
            repo,
            RuntimeError("Yahoo unavailable"),
            datetime(2026, 11, 24, 10, 30),
            source="yahoo_delayed",
        )
        table = repo.upserts[0]
        self.assertEqual(table[0], "data_source_status")
        self.assertEqual(table[1][0]["source"], "yahoo_delayed")
        self.assertEqual(table[1][0]["last_success_at"], "2026-11-24T10:00:00+00:00")
        self.assertIn("Yahoo unavailable", table[1][0]["last_error"])


if __name__ == "__main__":
    unittest.main()
