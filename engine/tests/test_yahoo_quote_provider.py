from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

from engine.providers.yahoo_quote_provider import CAIRO_TZ, YahooQuoteProvider


class YahooQuoteProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = YahooQuoteProvider(delay=0)
        self.source_time = datetime(2026, 11, 24, 10, 5, tzinfo=timezone.utc)

    def chart_response(self) -> Mock:
        response = Mock(status_code=200, ok=True)
        response.json.return_value = {
            "chart": {
                "result": [
                    {
                        "timestamp": [self.source_time.timestamp() - 86_400, self.source_time.timestamp()],
                        "indicators": {
                            "quote": [
                                {
                                    "close": [24.9, 25.1],
                                    "open": [24.8, 25.0],
                                    "high": [25.2, 25.3],
                                    "low": [24.7, 24.8],
                                    "volume": [1000, 1250],
                                }
                            ]
                        },
                        "meta": {"longName": "Commercial International Bank"},
                    }
                ]
            }
        }
        return response

    def test_daily_bars_are_normalised(self) -> None:
        self.provider.session.get = Mock(return_value=self.chart_response())

        batch = self.provider.fetch_quotes(("COMI",))

        self.assertEqual(batch.source, "yahoo_delayed")
        self.assertEqual(batch.delay_seconds, 86_400)
        quote = batch.quotes[0]
        self.assertEqual(quote.symbol, "COMI")
        self.assertEqual(quote.price, 25.1)
        self.assertEqual(quote.previous_close, 24.9)
        self.assertAlmostEqual(quote.change_pct, 0.8032, places=3)
        self.assertEqual(quote.volume, 1250)
        self.assertEqual(quote.source_timestamp, self.source_time.astimezone(CAIRO_TZ))

    def test_rate_limit_tries_the_next_host(self) -> None:
        limited = Mock(status_code=429, ok=False)
        self.provider.session.get = Mock(side_effect=[limited, self.chart_response()])
        self.provider.hosts = ("query1.finance.yahoo.com", "query2.finance.yahoo.com")

        batch = self.provider.fetch_quotes(("COMI",))

        self.assertEqual(len(batch.quotes), 1)
        self.assertEqual(self.provider.session.get.call_count, 2)
        self.assertIn("query2.finance.yahoo.com", self.provider.session.get.call_args.args[0])

    def test_short_optional_arrays_do_not_crash_parser(self) -> None:
        quote = YahooQuoteProvider._parse_symbol(
            "COMI",
            {
                "timestamp": [
                    self.source_time.timestamp() - 172_800,
                    self.source_time.timestamp() - 86_400,
                    self.source_time.timestamp(),
                ],
                "indicators": {
                    "quote": [
                        {
                            "close": [24.8, None, 25.1],
                            "open": [24.8],
                            "high": [],
                            "volume": [1000],
                        }
                    ]
                },
                "meta": {},
            },
        )

        self.assertIsNotNone(quote)
        assert quote is not None
        self.assertEqual(quote.price, 25.1)
        self.assertIsNone(quote.open)
        self.assertIsNone(quote.high)
        self.assertEqual(quote.volume, 0)


if __name__ == "__main__":
    unittest.main()
