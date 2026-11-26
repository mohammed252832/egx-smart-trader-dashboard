from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

import pandas as pd

from .config import Config
from .providers import (
    Bar,
    BorsaProvider,
    CsvProvider,
    HttpProvider,
    Provider,
    UniverseEntry,
    YahooProvider,
)


@dataclass
class Collected:
    universe: dict[str, UniverseEntry] = field(default_factory=dict)
    raw_bars: dict[str, dict[str, list[Bar]]] = field(default_factory=dict)
    source_rows: dict[str, int] = field(default_factory=dict)
    source_errors: dict[str, str] = field(default_factory=dict)
    sources_by_symbol: dict[str, list[str]] = field(default_factory=dict)


def _providers(config: Config) -> list[Provider]:
    providers: list[Provider] = []
    for prefix in config.provider_prefixes:
        provider_config = config.provider(prefix)
        if provider_config.enabled:
            providers.append(HttpProvider(provider_config, config.request_timeout))

    if config.yahoo_enabled:
        providers.append(
            YahooProvider(
                universe_url=config.yahoo_universe_url,
                symbols=config.universe.seed_symbols,
                range_=config.yahoo_range,
                hosts=config.yahoo_hosts,
                timeout=config.request_timeout,
            )
        )

    if config.borsa_enabled:
        providers.append(
            BorsaProvider(
                base_url=config.borsa_base_url,
                api_key=config.borsa_api_key,
                symbols=config.universe.seed_symbols,
                timeout=config.request_timeout,
            )
        )

    csv_provider = CsvProvider.from_env()
    if csv_provider.enabled:
        providers.append(csv_provider)

    if not providers:
        raise RuntimeError(
            "No real data provider configured: enable EGX_YAHOO_ENABLED / EGX_BORSA_ENABLED "
            "or set a licensed HTTP provider URL"
        )
    return providers


def collect(config: Config) -> Collected:
    """Fetch universe + history from every configured provider."""
    providers = _providers(config)
    collected = Collected()

    provider_universes: dict[str, list[UniverseEntry]] = {}
    for provider in providers:
        try:
            entries = provider.fetch_universe()
        except Exception as exc:
            entries = []
            provider.last_error = f"universe: {exc}"
        provider_universes[provider.name] = entries
        for entry in entries:
            collected.universe.setdefault(entry.symbol, entry)

    symbols = sorted(collected.universe)
    if not symbols:
        raise RuntimeError("No symbols returned by any data provider")

    def fetch_histories(active: list[Provider]) -> None:
        for provider in active:
            by_symbol: dict[str, list[Bar]] = {}
            for symbol in symbols:
                try:
                    bars = provider.fetch_history(symbol, config.history_days)
                except Exception as exc:
                    provider.last_error = f"history[{symbol}]: {exc}"
                    bars = []
                if bars:
                    by_symbol[symbol] = bars
                    collected.sources_by_symbol.setdefault(symbol, []).append(provider.name)

            collected.raw_bars[provider.name] = by_symbol
            collected.source_rows[provider.name] = sum(len(bars) for bars in by_symbol.values())
            if provider.last_error:
                collected.source_errors[provider.name] = provider.last_error
            elif collected.source_rows[provider.name] == 0:
                collected.source_errors[provider.name] = "no rows returned"

    # Quote-only providers are collected after a history provider has revealed
    # the real trading date, so their bars are not stamped with a fetch time.
    deferred = [provider for provider in providers if provider.needs_trade_date]
    fetch_histories([provider for provider in providers if not provider.needs_trade_date])

    trade_date = _resolve_trade_date(collected.raw_bars)
    if deferred:
        if trade_date is None:
            for provider in deferred:
                provider.last_error = "no history provider supplied a trade date"
        else:
            for provider in deferred:
                provider.bind_trade_date(trade_date)
            fetch_histories(deferred)

    for prefix in config.provider_prefixes:
        name = f"http_{prefix.lower()}"
        if name not in collected.source_rows:
            collected.source_rows[name] = 0
            collected.source_errors[name] = "not configured"

    for name in ("yahoo", "borsa"):
        if name not in collected.source_rows:
            collected.source_rows[name] = 0
            collected.source_errors[name] = "not configured"

    return collected


def _resolve_trade_date(raw_bars: dict[str, dict[str, list[Bar]]]) -> date | None:
    """Pick the latest real session from a history provider (Yahoo preferred)."""
    for name in ("yahoo", *raw_bars):
        dates = [bar.trade_date for bars in raw_bars.get(name, {}).values() for bar in bars]
        if dates:
            return max(dates)
    return None


def aggregate_bars(raw_bars: dict[str, dict[str, list[Bar]]]) -> dict[str, pd.DataFrame]:
    """Median close, max high, min low across sources for each trading day."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for source, by_symbol in raw_bars.items():
        for symbol, bars in by_symbol.items():
            bucket = grouped.setdefault(symbol, [])
            for bar in bars:
                bucket.append(
                    {
                        "trade_date": bar.trade_date,
                        "open": float(bar.open),
                        "high": float(bar.high),
                        "low": float(bar.low),
                        "close": float(bar.close),
                        "volume": float(bar.volume),
                        "source": source,
                    }
                )

    frames: dict[str, pd.DataFrame] = {}
    for symbol, rows in grouped.items():
        frame = pd.DataFrame(rows)
        frame["trade_date"] = pd.to_datetime(frame["trade_date"])
        aggregated = (
            frame.groupby("trade_date", as_index=False)
            .agg(
                open=("open", "first"),
                high=("high", "max"),
                low=("low", "min"),
                close=("close", "median"),
                volume=("volume", "max"),
            )
            .sort_values("trade_date")
            .reset_index(drop=True)
        )
        aggregated["symbol"] = symbol
        frames[symbol] = aggregated
    return frames
