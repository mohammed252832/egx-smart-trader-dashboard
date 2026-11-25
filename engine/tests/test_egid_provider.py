from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from engine.market_time import is_quote_market_time
from engine.providers.egid_provider import CAIRO_TZ, EgidQuoteProvider


class EgidProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = EgidQuoteProvider("user", "secret", delay_seconds=900)

    def test_bulk_quotes_are_normalised(self) -> None:
        payload = {
            "data": [
                {
                    "SYMBOL_CODE": "COMI.CA",
                    "ENG_NAME": "Commercial International Bank",
                    "LAST_PRICE": "25.10",
                    "PREV_CLOSE": "24.90",
                    "OPEN_PRICE": "25.00",
                    "HIGH_PRICE": "25.30",
                    "LOW_PRICE": "24.80",
                    "VOLUME": "1,250",
                    "TURNOVER": "31,300",
                    "LAST_UPDATE": "2026-11-24T12:05:00+02:00",
                },
                {
                    "symbol": "FWRY",
                    "price": 11.5,
                    "previousClose": 10.0,
                    "date": "2026-11-24",
                    "time": "12:06:00",
                },
                {"symbol": "BAD", "price": 0},
            ]
        }
        with patch.object(self.provider, "_get", return_value=payload):
            batch = self.provider.fetch_quotes()

        self.assertEqual(batch.source, "egid_delayed")
        self.assertEqual(batch.delay_seconds, 900)
        self.assertEqual(len(batch.quotes), 2)
        comi, fwry = batch.quotes
        self.assertEqual(comi.symbol, "COMI")
        self.assertEqual(comi.price, 25.10)
        self.assertEqual(comi.volume, 1250)
        self.assertAlmostEqual(comi.change_pct, 0.8032, places=3)
        self.assertEqual(comi.source_timestamp, datetime(2026, 11, 24, 12, 5, tzinfo=CAIRO_TZ))
        self.assertEqual(fwry.source_timestamp, datetime(2026, 11, 24, 12, 6, tzinfo=CAIRO_TZ))
        self.assertEqual(batch.source_timestamp, fwry.source_timestamp)

    def test_requested_symbols_limit_the_bulk_feed(self) -> None:
        payload = [
            {"symbol": "COMI", "price": 25.1},
            {"symbol": "FWRY", "price": 11.5},
        ]
        with patch.object(self.provider, "_get", return_value=payload):
            batch = self.provider.fetch_quotes(("COMI",))

        self.assertEqual([quote.symbol for quote in batch.quotes], ["COMI"])

    def test_empty_or_invalid_quotes_fail_loudly(self) -> None:
        with patch.object(self.provider, "_get", return_value=[{"symbol": "COMI", "price": None}]):
            with self.assertRaisesRegex(RuntimeError, "no usable quotes"):
                self.provider.fetch_quotes()

    def test_token_response_variants_are_supported(self) -> None:
        response = Mock(ok=True)
        response.json.return_value = {"data": {"accessToken": "jwt-value"}}
        self.provider.session.post = Mock(return_value=response)
        self.assertEqual(self.provider._get_token(), "jwt-value")
        self.provider.session.post.assert_called_once()
        self.assertEqual(
            self.provider.session.post.call_args.kwargs["json"],
            {"Username": "user", "Password": "secret"},
        )

    def test_message_is_not_mistaken_for_a_token(self) -> None:
        response = Mock(ok=True)
        response.json.return_value = {"message": "credentials required"}
        self.provider.session.post = Mock(return_value=response)
        with self.assertRaisesRegex(RuntimeError, "did not contain a token"):
            self.provider._get_token()

    def test_unauthorized_request_refreshes_token_once(self) -> None:
        unauthorized = Mock(status_code=401, ok=False)
        success = Mock(status_code=200, ok=True)
        success.json.return_value = [{"symbol": "COMI", "price": 25}]
        self.provider._access_token = "expired"
        self.provider.session.get = Mock(side_effect=[unauthorized, success])
        with patch.object(self.provider, "_get_token", return_value="fresh") as get_token:
            payload = self.provider._get("/api/DelayedFeed/getAllMarketWatch")

        self.assertEqual(payload[0]["symbol"], "COMI")
        get_token.assert_called_once_with()
        self.assertEqual(self.provider.session.get.call_count, 2)
        self.assertEqual(self.provider.session.get.call_args.kwargs["headers"]["Authorization"], "Bearer fresh")


class MarketTimeTests(unittest.TestCase):
    def test_refresh_window_uses_cairo_time(self) -> None:
        cairo = ZoneInfo("Africa/Cairo")
        self.assertTrue(is_quote_market_time(datetime(2026, 11, 22, 10, 30, tzinfo=cairo)))
        self.assertTrue(is_quote_market_time(datetime(2026, 11, 24, 14, 45, tzinfo=cairo)))
        self.assertFalse(is_quote_market_time(datetime(2026, 11, 27, 12, 0, tzinfo=cairo)))
        self.assertFalse(is_quote_market_time(datetime(2026, 11, 24, 15, 30, tzinfo=cairo)))
        self.assertTrue(is_quote_market_time(datetime(2026, 11, 24, 10, 0, tzinfo=ZoneInfo("UTC"))))


if __name__ == "__main__":
    unittest.main()
