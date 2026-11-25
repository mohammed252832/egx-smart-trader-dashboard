from __future__ import annotations

import logging
import math
import re
from datetime import datetime, timezone

try:  # optional, useful for local runs
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from .aggregator import aggregate_bars, collect
from .config import Config
from .evaluate import evaluate_outcomes
from .features import FEATURE_COLUMNS, build_features
from .model import predict_probability, train_model
from .model_report import write_model_report
from .quality import apply_universe_filters, filter_bars
from .repository import SupabaseRepository
from .risk import TradePlan, build_plan

LOG = logging.getLogger("egx.run")
_MARKET_DATE_RE = re.compile(r"market_date=(\d{4}-\d{2}-\d{2})")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _last_market_date(repo: SupabaseRepository) -> str | None:
    rows = repo.select(
        "analysis_runs",
        columns="market_date,notes",
        params={"status": "eq.success", "order": "finished_at.desc", "limit": 1},
    )
    for row in rows:
        market_date = row.get("market_date")
        if market_date:
            return str(market_date)[:10]
        match = _MARKET_DATE_RE.search(str(row.get("notes") or ""))
        if match:
            return match.group(1)
    return None


def _finish(
    repo: SupabaseRepository,
    run_id: str,
    status: str,
    notes: str,
    **metadata: object,
) -> None:
    payload = {"status": status, "finished_at": _now(), "notes": notes[:2000], **metadata}
    repo.update("analysis_runs", payload, {"id": f"eq.{run_id}"})


def _run(config: Config, repo: SupabaseRepository) -> int:
    created = repo.insert(
        "analysis_runs",
        [
            {
                "started_at": _now(),
                "status": "running",
                "model_version": config.model_version,
                "notes": f"horizon={config.horizon_days}; top_n={config.top_n}",
            }
        ],
    )
    run_id = created[0]["id"]

    try:
        collected = collect(config)
        LOG.info(
            "Collected %d symbol(s) from: %s",
            len(collected.universe),
            ", ".join(sorted(collected.source_rows)),
        )
        for source, error in collected.source_errors.items():
            LOG.warning("Source %s: %s", source, error)

        cleaned, quality = filter_bars(collected.raw_bars, config.universe)
        LOG.info(
            "Quality: kept %d/%d bars (invalid=%d, ohlc=%d, jumps=%d, ranges=%d)",
            quality.kept_rows,
            quality.raw_rows,
            quality.invalid_prices,
            quality.invalid_ohlc,
            quality.impossible_jumps,
            quality.extreme_ranges,
        )
        if not quality.kept_rows:
            raise RuntimeError("No usable price bars after data-quality checks")

        aggregated_frames = aggregate_bars(cleaned)
        eligible, dropped, flags = apply_universe_filters(aggregated_frames, config.universe)
        LOG.info(
            "Universe: eligible=%d, dropped=%d, flagged=%d",
            len(eligible),
            len(dropped),
            len(flags),
        )
        if len(eligible) < config.universe.minimum_universe_size:
            raise RuntimeError(
                f"Only {len(eligible)} eligible symbols; "
                f"minimum is {config.universe.minimum_universe_size}"
            )

        as_of = max(frame["trade_date"].max() for frame in eligible.values()).date().isoformat()
        previous_market_date = _last_market_date(repo)
        if previous_market_date and as_of <= previous_market_date:
            _finish(
                repo,
                run_id,
                "skipped",
                f"market_date={as_of}; no new session after {previous_market_date}",
                market_date=as_of,
                universe_size=len(eligible),
                symbols_requested=len(collected.universe),
                symbols_fetched=len(aggregated_frames),
                symbols_eligible=len(eligible),
                symbols_dropped=len(dropped),
                drop_reasons=dropped,
                quality_report=quality.as_dict(),
            )
            LOG.info("No new trading session (%s); skipped publishing", as_of)
            return 0

        feature_frames = {symbol: build_features(frame) for symbol, frame in eligible.items()}
        model = train_model(feature_frames, config)
        LOG.info(
            "Model %s trained on %d rows (validation accuracy: %s)",
            model.version,
            model.train_rows,
            "n/a" if model.validation_accuracy is None else f"{model.validation_accuracy:.3f}",
        )
        LOG.info("Model report written to %s", write_model_report(model, config))

        ranked: list[tuple[TradePlan, str]] = []
        for symbol, frame in feature_frames.items():
            if frame.empty:
                continue
            latest = frame.iloc[-1]
            values = {name: float(latest[name]) for name in FEATURE_COLUMNS}
            probability = predict_probability(model.estimator, values)
            atr = float(latest["atr"])
            if not math.isfinite(atr) or atr <= 0:
                atr = float(latest["close"]) * 0.01
            lookback = config.signals.risk.support_lookback
            recent = frame.tail(lookback)
            support = float(recent["low"].min())
            resistance = float(recent["high"].max())
            previous_close = (
                float(frame.iloc[-2]["close"]) if len(frame) > 1 else float(latest["close"])
            )
            plan = build_plan(
                probability,
                values,
                float(latest["close"]),
                previous_close,
                atr,
                config,
                support=support,
                resistance=resistance,
            )
            ranked.append((plan, symbol))

        ranked.sort(key=lambda item: item[0].score, reverse=True)
        top = ranked[: config.top_n]
        if not top:
            raise RuntimeError("No recommendations could be produced")

        existing_status = {
            row["source"]: row
            for row in repo.select("data_source_status", columns="source,last_success_at", params={"limit": 500})
        }
        status_at = _now()
        repo.upsert(
            "data_source_status",
            [
                {
                    "source": source,
                    "last_success_at": status_at if row_count > 0 else existing_status.get(source, {}).get("last_success_at"),
                    "last_error": collected.source_errors.get(source),
                    "rows_written": row_count,
                    "updated_at": status_at,
                }
                for source, row_count in collected.source_rows.items()
            ],
            "source",
        )

        repo.upsert(
            "stocks",
            [
                {
                    "symbol": entry.symbol,
                    "name": entry.name,
                    "sector": entry.sector,
                    "is_active": entry.symbol in eligible,
                    "updated_at": _now(),
                }
                for entry in collected.universe.values()
            ],
            "symbol",
        )

        for source, by_symbol in cleaned.items():
            rows = [
                {
                    "symbol": symbol,
                    "trade_date": bar.trade_date.isoformat(),
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                    "source": source,
                    "adjusted": False,
                    "updated_at": _now(),
                }
                for symbol, bars in by_symbol.items()
                for bar in bars
            ]
            if rows:
                repo.upsert("price_bars", rows, "symbol,trade_date,source")

        merged_rows = [
            {
                "symbol": symbol,
                "trade_date": row["trade_date"].date().isoformat(),
                "open": round(float(row["open"]), 4),
                "high": round(float(row["high"]), 4),
                "low": round(float(row["low"]), 4),
                "close": round(float(row["close"]), 4),
                "volume": int(row["volume"]),
                "source": "aggregated",
                "adjusted": False,
                "updated_at": _now(),
            }
            for symbol, frame in eligible.items()
            for _, row in frame.iterrows()
        ]
        repo.upsert("price_bars", merged_rows, "symbol,trade_date,source")

        repo.insert(
            "recommendations",
            [
                {
                    "run_id": run_id,
                    "symbol": symbol,
                    "as_of": as_of,
                    "horizon_days": config.horizon_days,
                    "entry_price": plan.entry_price,
                    "target_price": plan.target_price,
                    "stop_loss": plan.stop_loss,
                    "upside_pct": plan.upside_pct,
                    "risk_pct": plan.risk_pct,
                    "reward_risk": plan.reward_risk,
                    "score": plan.score,
                    "probability": plan.probability,
                    "confidence": plan.confidence,
                    "signal": plan.signal,
                    "sources": sorted(set(collected.sources_by_symbol.get(symbol, []) + ["aggregated"])),
                    "created_at": _now(),
                }
                for plan, symbol in top
            ],
        )

        evaluated = evaluate_outcomes(repo, config)
        signal_metrics = (model.metrics or {}).get("signals") or {}
        hit_note = (
            f"; hit_rate={signal_metrics.get('buy_hit_rate')}" if signal_metrics else ""
        )
        _finish(
            repo,
            run_id,
            "success",
            (
                f"market_date={as_of}; model={model.version}; "
                f"validation_accuracy={model.validation_accuracy}; outcomes={evaluated}{hit_note}"
            ),
            market_date=as_of,
            universe_size=len(eligible),
            symbols_requested=len(collected.universe),
            symbols_fetched=len(aggregated_frames),
            symbols_eligible=len(eligible),
            symbols_dropped=len(dropped),
            drop_reasons=dropped,
            quality_report=quality.as_dict(),
        )
        LOG.info("Run complete: as_of=%s, recommendations=%d", as_of, len(top))
        return 0

    except Exception as exc:
        LOG.exception("Analysis run failed")
        try:
            repo.update(
                "analysis_runs",
                {"status": "failed", "finished_at": _now(), "notes": str(exc)[:2000]},
                {"id": f"eq.{run_id}"},
            )
        except Exception:
            LOG.exception("Could not mark the run as failed")
        return 1


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = Config.from_env()
    if not config.supabase_url or not config.supabase_secret_key:
        LOG.error("SUPABASE_URL and SUPABASE_SECRET_KEY must be set")
        return 2
    repo = SupabaseRepository(config.supabase_url, config.supabase_secret_key, config.request_timeout)
    return _run(config, repo)


if __name__ == "__main__":
    raise SystemExit(main())
