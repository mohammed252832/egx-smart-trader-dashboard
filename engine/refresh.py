from __future__ import annotations

import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .config import Config
from .market_time import CAIRO_TZ, is_quote_market_time
from .providers.base import Quote, QuoteBatch
from .providers.egid_provider import EgidPublicQuoteProvider, EgidQuoteProvider
from .providers.tradingview_provider import TradingViewQuoteProvider
from .providers.yahoo_quote_provider import YahooQuoteProvider
from .repository import SupabaseRepository

LOG = logging.getLogger("egx.refresh")


@dataclass(frozen=True)
class SourcedQuote:
    quote: Quote
    source: str
    delay_seconds: int


@dataclass(frozen=True)
class RefreshBatch:
    quotes: tuple[SourcedQuote, ...]
    source: str
    source_timestamp: datetime | None
    delay_seconds: int
    errors: tuple[str, ...] = ()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _symbol(value: Any) -> str:
    symbol = str(value or "").strip().upper().removesuffix(".CA")
    return symbol if symbol.isalnum() else ""


def _tracked_symbols(config: Config, repo: SupabaseRepository) -> tuple[str, ...]:
    try:
        rows = repo.select(
            "latest_market",
            columns="symbol",
            params={"order": "liquidity_rank.asc", "limit": config.market_universe_size},
        )
    except Exception:
        LOG.exception("Could not read the liquid market universe; using configured seed symbols")
        rows = []

    symbols = tuple(
        dict.fromkeys(
            symbol
            for row in rows
            if (symbol := _symbol(row.get("symbol")))
        )
    )[: config.market_universe_size]
    if symbols:
        return symbols

    return tuple(
        dict.fromkeys(
            symbol
            for value in config.universe.seed_symbols
            if (symbol := _symbol(value))
        )
    )[: config.market_universe_size]


def _quote_providers(config: Config) -> list[Any]:
    providers: list[Any] = []
    if config.egid_enabled and config.egid_username and config.egid_password:
        providers.append(
            EgidQuoteProvider(
                username=config.egid_username,
                password=config.egid_password,
                base_url=config.egid_base_url,
                timeout=config.request_timeout,
                delay_seconds=config.egid_delay_seconds,
            )
        )
    if config.egid_public_enabled:
        providers.append(
            EgidPublicQuoteProvider(
                ticker_url=config.egid_public_ticker_url,
                timeout=config.request_timeout,
                delay_seconds=config.egid_public_delay_seconds,
            )
        )
    if config.tradingview_enabled:
        providers.append(
            TradingViewQuoteProvider(
                scanner_url=config.tradingview_scanner_url,
                timeout=config.request_timeout,
                delay_seconds=config.tradingview_delay_seconds,
                chunk_size=config.tradingview_chunk_size,
            )
        )
    if config.yahoo_quote_enabled:
        providers.append(
            YahooQuoteProvider(
                hosts=config.yahoo_hosts,
                timeout=config.request_timeout,
                delay=config.yahoo_quote_delay_seconds,
            )
        )
    return providers


def _tracked_batch(batch: QuoteBatch, symbols: tuple[str, ...]) -> QuoteBatch:
    wanted = set(symbols)
    quotes = tuple(dict.fromkeys(quote for quote in batch.quotes if quote.symbol in wanted))
    if not quotes:
        raise RuntimeError(f"{batch.source} returned no quotes for tracked symbols")
    timestamps = [quote.source_timestamp for quote in quotes if quote.source_timestamp]
    return QuoteBatch(
        source=batch.source,
        quotes=quotes,
        source_timestamp=max(timestamps) if timestamps else None,
        delay_seconds=batch.delay_seconds,
        errors=batch.errors,
    )


def _fetch_quotes(providers: list[Any], symbols: tuple[str, ...]) -> RefreshBatch:
    failures: list[str] = []
    warnings: list[str] = []
    collected: dict[str, SourcedQuote] = {}
    remaining = symbols

    for provider in providers:
        if not remaining:
            break
        try:
            batch = _tracked_batch(provider.fetch_quotes(remaining), remaining)
        except Exception as exc:
            message = f"{provider.name}: {type(exc).__name__}: {exc}"
            failures.append(message)
            LOG.warning("Quote source failed: %s", message)
            continue

        received = {quote.symbol for quote in batch.quotes}
        for quote in batch.quotes:
            collected.setdefault(quote.symbol, SourcedQuote(quote, batch.source, batch.delay_seconds))
        warnings.extend(batch.errors)
        missing = tuple(symbol for symbol in remaining if symbol not in received)
        if missing:
            warnings.append(f"{batch.source} missing {len(missing)} tracked symbols")
        if failures:
            LOG.warning("Using %s after source fallback: %s", batch.source, "; ".join(failures))
        remaining = missing

    if not collected:
        raise RuntimeError("All quote sources failed: " + "; ".join(failures))

    if remaining:
        warnings.append(f"{len(remaining)} tracked symbols still unavailable after all sources")
    quotes = tuple(collected.values())
    sources = tuple(dict.fromkeys(item.source for item in quotes))
    timestamps = [item.quote.source_timestamp for item in quotes if item.quote.source_timestamp]
    return RefreshBatch(
        quotes=quotes,
        source=sources[0] if len(sources) == 1 else "mixed",
        source_timestamp=max(timestamps) if timestamps else None,
        delay_seconds=max(item.delay_seconds for item in quotes),
        errors=tuple(dict.fromkeys((*failures, *warnings))),
    )


def _status_payload(
    batch: RefreshBatch,
    fetched_at: datetime,
    errors: Iterable[str] = (),
) -> dict:
    market_date = (
        batch.source_timestamp.astimezone(CAIRO_TZ).date()
        if batch.source_timestamp
        else None
    )
    messages = tuple(dict.fromkeys(errors))
    return {
        "source": batch.source,
        "last_success_at": fetched_at.isoformat(),
        "last_error": "; ".join(messages)[:1000] if messages else None,
        "rows_written": len(batch.quotes),
        "source_timestamp": batch.source_timestamp.isoformat() if batch.source_timestamp else None,
        "delay_seconds": batch.delay_seconds,
        "market_date": market_date.isoformat() if market_date else None,
        "updated_at": fetched_at.isoformat(),
    }


def _record_failure(
    repo: SupabaseRepository,
    exc: Exception,
    attempted_at: datetime,
    *,
    source: str,
) -> None:
    rows = repo.select(
        "data_source_status",
        columns="source,last_success_at,rows_written,source_timestamp,delay_seconds,market_date",
        params={"source": f"eq.{source}", "limit": 1},
    )
    existing = rows[0] if rows else {}
    default_delay = 86_400 if source == YahooQuoteProvider.name else 900
    repo.upsert(
        "data_source_status",
        [
            {
                "source": source,
                "last_success_at": existing.get("last_success_at"),
                "last_error": f"{type(exc).__name__}: {exc}"[:1000],
                "rows_written": existing.get("rows_written", 0),
                "source_timestamp": existing.get("source_timestamp"),
                "delay_seconds": existing.get("delay_seconds", default_delay),
                "market_date": existing.get("market_date"),
                "updated_at": attempted_at.isoformat(),
            }
        ],
        "source",
    )


def _refresh(config: Config, repo: SupabaseRepository) -> int:
    now = datetime.now(CAIRO_TZ)
    force = os.getenv("EGX_QUOTE_FORCE_REFRESH", "").strip().lower() in {"1", "true", "yes", "on"}
    if not force and not is_quote_market_time(now):
        LOG.info("Outside EGX quote refresh hours; skipped")
        return 0

    providers = _quote_providers(config)
    if not providers:
        LOG.error("Enable at least one quote source: EGID, TradingView, or Yahoo")
        return 2

    attempted_at = _now()
    active_source = providers[0].name
    try:
        symbols = _tracked_symbols(config, repo)
        if not symbols:
            raise RuntimeError("No tracked symbols are configured")
        batch = _fetch_quotes(providers, symbols)
        active_source = batch.source
        warnings = batch.errors

        existing_stocks = {
            row["symbol"]: row
            for row in repo.select("stocks", columns="symbol,name", params={"limit": 1000})
        }
        missing_stocks = [
            {"symbol": item.quote.symbol, "name": item.quote.name or item.quote.symbol, "updated_at": attempted_at.isoformat()}
            for item in batch.quotes
            if item.quote.symbol not in existing_stocks
        ]
        if missing_stocks:
            repo.upsert("stocks", missing_stocks, "symbol")

        fetched_at = _now()
        repo.upsert(
            "live_quotes",
            [
                {
                    "symbol": item.quote.symbol,
                    "price": item.quote.price,
                    "previous_close": item.quote.previous_close,
                    "change_pct": item.quote.change_pct,
                    "open": item.quote.open,
                    "high": item.quote.high,
                    "low": item.quote.low,
                    "volume": item.quote.volume,
                    "turnover": item.quote.turnover,
                    "source": item.source,
                    "source_timestamp": item.quote.source_timestamp.isoformat() if item.quote.source_timestamp else None,
                    "delay_seconds": item.delay_seconds,
                    "market_date": item.quote.source_timestamp.astimezone(CAIRO_TZ).date().isoformat()
                    if item.quote.source_timestamp
                    else None,
                    "fetched_at": fetched_at.isoformat(),
                }
                for item in batch.quotes
            ],
            "symbol",
        )
        repo.upsert("data_source_status", [_status_payload(batch, fetched_at, warnings)], "source")
        LOG.info(
            "Refreshed %d quotes from %s; source_time=%s; delay=%ss; warnings=%d",
            len(batch.quotes),
            batch.source,
            batch.source_timestamp.isoformat() if batch.source_timestamp else "unknown",
            batch.delay_seconds,
            len(warnings),
        )
        return 0
    except Exception as exc:
        LOG.exception("Quote refresh failed")
        try:
            _record_failure(repo, exc, attempted_at, source=active_source)
        except Exception:
            LOG.exception("Could not record quote refresh failure")
        return 1


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = Config.from_env()
    if not config.supabase_url or not config.supabase_secret_key:
        LOG.error("SUPABASE_URL and SUPABASE_SECRET_KEY must be set")
        return 2
    repo = SupabaseRepository(config.supabase_url, config.supabase_secret_key, config.request_timeout)
    return _refresh(config, repo)


if __name__ == "__main__":
    raise SystemExit(main())
