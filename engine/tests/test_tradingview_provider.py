from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

from engine.providers.tradingview_provider import CAIRO_TZ, COLUMNS, TradingViewQuoteProvider


class TradingViewProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = TradingViewQuoteProvider(delay_seconds=900)
        self.source_time = datetime(2026, 11, 24, 12, 5, tzinfo=timezone.utc)

    def response(self, rows: list[dict]) -> Mock:
        response = Mock(ok=True, status_code=200)
        response.json.return_value = {"data": rows}
        return response

    def test_bulk_quotes_are_normalised(self) -> None:
        row = {
            "s": "EGX:COMI",
            "d": [
                "Commercial International Bank",
                10.0,
                -9.09,
                -1.0,
                1250,
                9.8,
                11.2,
                10.5,
                None,
                self.source_time.timestamp(),
            ],
        }
        self.provider.session.post = Mock(return_value=self.response([row]))

        batch = self.provider.fetch_quotes(("comi", "COMI.CA"))

        self.provider.session.post.assert_called_once()
        self.assertEqual(
            self.provider.session.post.call_args.kwargs["json"]["symbols"]["tickers"],
            ["EGX:COMI"],
        )
        self.assertEqual(batch.source, "tradingview_delayed")
        self.assertEqual(batch.delay_seconds, 900)
        self.assertEqual(len(batch.quotes), 1)
        quote = batch.quotes[0]
        self.assertEqual(quote.symbol, "COMI")
        self.assertEqual(quote.name, "Commercial International Bank")
        self.assertEqual(quote.price, 10.0)
        self.assertEqual(quote.previous_close, 11.0)
        self.assertEqual(quote.high, 10.0)
        self.assertEqual(quote.low, 10.0)
        self.assertEqual(quote.volume, 1250)
        self.assertEqual(quote.source_timestamp, self.source_time.astimezone(CAIRO_TZ))
        self.assertEqual(batch.source_timestamp, self.source_time.astimezone(CAIRO_TZ))

    def test_missing_symbols_are_reported_without_discarding_good_quotes(self) -> None:
        row = {"s": "EGX:COMI", "d": ["COMI", 25.1] + [None] * (len(COLUMNS) - 2)}
        self.provider.session.post = Mock(return_value=self.response([row]))

        batch = self.provider.fetch_quotes(("COMI", "FWRY"))

        self.assertEqual([quote.symbol for quote in batch.quotes], ["COMI"])
        self.assertEqual(len(batch.errors), 1)
        self.assertIn("FWRY", batch.errors[0])

    def test_250_symbols_are_split_into_three_default_chunks(self) -> None:
        self.provider = TradingViewQuoteProvider(chunk_size=100)
        symbols = tuple(f"SYM{index}" for index in range(250))
        self.provider.session.post = Mock(
            side_effect=lambda *args, **kwargs: self.response([
                {"s": f"EGX:{symbol}", "d": [symbol, 25.1] + [None] * (len(COLUMNS) - 2)}
                for symbol in kwargs["json"]["symbols"]["tickers"]
            ])
        )

        batch = self.provider.fetch_quotes(symbols)

        self.assertEqual(self.provider.session.post.call_count, 3)
        self.assertEqual(len(batch.quotes), 250)
        self.assertEqual(batch.errors, ())

    def test_no_usable_quotes_fail_loudly(self) -> None:
        self.provider.session.post = Mock(return_value=self.response([]))

        with self.assertRaisesRegex(RuntimeError, "no usable EGX quotes"):
            self.provider.fetch_quotes(("COMI",))


if __name__ == "__main__":
    unittest.main()
