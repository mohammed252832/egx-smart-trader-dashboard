# EGX Smart Trader — Phase 0 Audit

Date: 2026-11-20
Branch: `improve/phase-0-audit`
Scope: read-only exploration of the whole repository. No source code was changed in this phase.

## 1. Folder structure

Tracked files (`git ls-files`), grouped by role:

```
.env.example                     Environment variable template (placeholders only)
AGENTS.md                        Agent rules (phase instructions); Next.js auto-note appended
README.md                        Setup / deployment documentation
app/
  api/recommendations/route.ts   JSON endpoint, delegates to lib/data.ts
  favicon.ico, globals.css       Static asset + Tailwind entry
  layout.tsx                     Root layout: lang="ar", dir="rtl", metadata
  page.tsx                       Single dashboard page (server component)
engine/
  __init__.py
  aggregator.py                  Provider orchestration, deferred date binding, bar merging
  config.py                      Env-driven Config / ProviderConfig dataclasses
  evaluate.py                    Post-hoc recommendation outcome evaluation
  features.py                    19 technical features (FEATURE_COLUMNS)
  model.py                       XGBoost classifier + heuristic fallback
  providers/
    __init__.py
    base.py                      Bar, UniverseEntry, Provider ABC (+ bind_trade_date hook)
    borsa_provider.py            Borsa /v1/stocks + /v1/quotes adapter (quote-only)
    csv_provider.py              Optional local CSV source
    http_provider.py             Generic env-driven REST adapter (placeholders)
    sample_provider.py           Deterministic synthetic data (safety net)
    yahoo_provider.py            EGID universe + Yahoo Finance .CA daily bars
  repository.py                  Thin PostgREST client (secret key)
  requirements.txt
  risk.py                        TradePlan: entry/target/stop, score, signal
  run.py                         Main pipeline entry point (python -m engine.run)
  sample_data/universe.csv       34 sample symbols (symbol,name,sector)
eslint.config.mjs
lib/
  data.ts                        Supabase read + stats + demo fallback
  supabase.ts                    Supabase client factory (publishable key)
  types.ts                       Recommendation / DashboardData types
next.config.ts                   Next 16 cacheComponents, Turbopack, Tailwind loader
package.json                     Next 16.4.6 / React 19 / Supabase JS / ESLint
package-lock.json
public/                          Default Next.js SVG assets
supabase/
  reset.sql                      Drops all EGX tables/view (destructive)
  schema.sql                     Tables, view, RLS policies, grants
.github/workflows/
  analyze.yml                    Scheduled engine run + Vercel refresh
  deploy.yml                     Vercel deploy hook on frontend pushes
```

No `supabase/migrations/` directory exists. No test files (TS or Python) exist.

## 2. Pipeline flow (end to end)

1. **Trigger** — `.github/workflows/analyze.yml` runs on cron `0 3 * * 0-4` or `workflow_dispatch`.
2. **Config** — `engine/config.py` reads env vars into an immutable `Config`.
3. **Collection** — `engine/aggregator.py:collect()`:
   - Builds providers: generic `HttpProvider`s for configured prefixes (`DATACEDAR`, `EGID`, `BORSA`, `EGX`), then `YahooProvider`, then `BorsaProvider`, then `CsvProvider`, then (if enabled) `SampleProvider`.
   - Calls `fetch_universe()` on each; merges `UniverseEntry` by symbol (first provider wins).
   - Fetches history from providers with `needs_trade_date == False` first.
   - `_resolve_trade_date()` prefers Yahoo's latest bar date, else any provider's; calls `bind_trade_date()` on deferred quote-only providers (Borsa), then fetches their history.
   - Records `source_rows`, `source_errors`, `sources_by_symbol`.
4. **Persistence** — `engine/run.py` upserts `data_source_status`, `stocks`, and raw `price_bars` per source, then writes `source = "aggregated"` bars.
5. **Aggregation** — `aggregate_bars()` takes first `open`, max `high`, min `low`, median `close`, max reported `volume` per `(symbol, trade_date)` so duplicate provider snapshots are not summed.
6. **Features** — `build_features()` produces 19 indicators; NaNs/Infs are replaced with `0.0`.
7. **Model** — `train_model()` builds labels (`forward_return >= target_pct` after `horizon_days`), sorts by date, splits 80/20 by row position, fits `XGBClassifier`; falls back to `HeuristicModel` if <150 rows or one class. Logs `validation_accuracy` into `analysis_runs.notes`.
8. **Ranking** — for each symbol, `predict_probability()` + `build_plan()` produce `TradePlan`; sorted by `score` desc; top `EGX_TOP_N` (10) inserted into `recommendations`.
9. **Evaluation** — `evaluate_outcomes()` reads pending recommendations, walks `aggregated` bars after `as_of`, resolves win/loss/flat (target before stop when both touched on the same date), upserts `recommendation_outcomes`.
10. **Refresh** — successful run POSTs `VERCEL_DEPLOY_HOOK` to redeploy the dashboard.

## 3. Data sources

| Source | Adapter | Data | Status / notes |
| --- | --- | --- | --- |
| EGID public feed | `YahooProvider` | Universe (`GetAllMarketWatchNames`, 308 `.CA` tickers) | Anonymous, no token |
| Yahoo Finance | `YahooProvider` | Daily OHLCV bars for `.CA` tickers, `range=2y` | Primary history; 40-symbol default list in code; ~15,600 rows last run |
| Borsa (open source) | `BorsaProvider` | `/v1/stocks` universe + sectors, `/v1/quotes` latest price | 39 quote rows last run; demo host has a 50 req/day limit; no history endpoint; volume set to 0 to avoid double counting |
| Generic HTTP | `HttpProvider` | Universe/history from `{symbol}`, `{days}`, `{api_key}` URL templates | All four prefixes currently unconfigured (`not configured`) |
| CSV | `CsvProvider` | Local universe + one CSV per symbol | Not configured; stale error row exists in DB |
| Sample | `SampleProvider` | Deterministic synthetic OHLCV | Default `EGX_USE_SAMPLE=true`; currently disabled via GitHub Secret |

Borsa quotes are Yahoo-derived and are deliberately stamped with Yahoo's latest trading date rather than the quote's fetch timestamp.

## 4. Database tables and columns in use

Source of truth: `supabase/schema.sql` (no migrations).

| Table | Columns | Written by | Read by |
| --- | --- | --- | --- |
| `stocks` | symbol (PK), name, sector, is_active, updated_at | run.py (universe upsert) | view, evaluate (via FK) |
| `price_bars` | symbol+trade_date+source (PK), open, high, low, close, volume, adjusted, updated_at | run.py (raw per source + `aggregated`) | evaluate, aggregate_bars |
| `analysis_runs` | id (PK), started_at, finished_at, status, model_version, universe_size, notes | run.py | view (latest successful run) |
| `recommendations` | id (PK), run_id, symbol, as_of, horizon_days, entry_price, target_price, stop_loss, upside_pct, risk_pct, reward_risk, score, confidence, signal, sources, created_at | run.py | view, evaluate |
| `recommendation_outcomes` | recommendation_id (PK), evaluated_at, exit_date, exit_price, max_high, min_low, hit_target, hit_stop, return_pct, outcome | evaluate.py | view |
| `data_source_status` | source (PK), last_success_at, last_error, rows_written, updated_at | run.py | not read by app |
| view `top_recommendations` | id, symbol, name, as_of, horizon_days, entry/target/stop, upside/risk/reward_risk, score, confidence, signal, sources, return_pct, outcome | — | `lib/data.ts` |

RLS is enabled on all six tables with `select` policies for `anon, authenticated`; the view uses `security_invoker = true` and is granted `select`. No `insert/update/delete` policies exist for public roles.

## 5. Frontend data access

- `lib/supabase.ts` reads `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`; returns `null` if either is missing. Vercel currently supplies the **publishable** key under the legacy-named variable.
- `lib/data.ts:getDashboardData()` is a cached server function (`"use cache"`, `cacheLife("minutes")`). It selects `*` from `top_recommendations LIMIT 10`. On any error **or empty result**, it silently returns `demoData()` (10 hard-coded synthetic rows with Arabic names) with `isDemo: true`.
- `buildStats()` derives `analyzed = rows.length` (i.e. 10), `avgUpside` over those 10 rows, and `winRate` only from `outcome in {win,loss}` **within the current top-10 rows**.
- `app/page.tsx` renders a single RTL page: three stat cards, a 9-column table (`min-w-[1100px]`), and two explanatory panels. `app/api/recommendations/route.ts` exposes the same payload as JSON.
- No disclaimer, methodology page, detail page, history page, filters, sorting, search, tooltips, or mobile card layout. Numeric formatting uses `en-EG`; company names come from the DB and are English.

## 6. GitHub Actions workflows

| Workflow | Trigger | What it does |
| --- | --- | --- |
| `analyze.yml` | `cron: 0 3 * * 0-4`, `workflow_dispatch` | Installs `engine/requirements.txt`, passes all secrets as env, runs `python -m engine.run`, then POSTs the Vercel deploy hook |
| `deploy.yml` | push to `main` on `app/**`, `lib/**`, `package*.json`, `next.config.ts`, workflow file; `workflow_dispatch` | POSTs the same Vercel deploy hook |

Timing note: 03:00 UTC is 05:00 Cairo in EET (UTC+2) and 06:00 in EEST (UTC+3). EGX trades ~10:00–14:30 Cairo, so the run happens **before** that day's session and necessarily publishes the previous session's data. GitHub cron is UTC-only and cannot express DST.

## 7. Environment variables

**Frontend (Vercel, non-secret `NEXT_PUBLIC_*`):**
`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` (holds a `sb_publishable_...` value).

**Engine (GitHub Actions Secrets):**
`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `EGX_USE_SAMPLE`, `EGX_HISTORY_DAYS`, `EGX_HORIZON_DAYS`, `EGX_TOP_N`, `EGX_TARGET_PCT`, `EGX_STOP_ATR`, `EGX_TARGET_ATR`, `EGX_MAX_STOP_PCT`, `EGX_MODEL_VERSION`, `EGX_REQUEST_TIMEOUT`, `EGX_PROVIDERS`, `EGX_SYMBOLS`, `EGX_YAHOO_ENABLED`, `EGX_YAHOO_RANGE`, `EGX_YAHOO_UNIVERSE_URL`, `EGX_YAHOO_HOSTS`, `EGX_BORSA_ENABLED`, `EGX_BORSA_BASE_URL`, `EGX_BORSA_API_KEY`, `VERCEL_DEPLOY_HOOK`, plus `{DATACEDAR,EGID,BORSA,EGX}_{API_KEY,UNIVERSE_URL,HISTORY_URL}` and optional `EGX_UNIVERSE_CSV`, `EGX_HISTORY_DIR`.

`config.py` defaults: sample **true**, Yahoo false, Borsa false, history 400 days, horizon 3, top 10, timeout 20s.

## 8. Tests and quality gates

- No unit, integration, or e2e tests in the repository (`package.json` has no `test` script; no `pytest`/`unittest` files).
- No CI lint/typecheck job. `npm run lint` exists locally; `next build` happens on Vercel.
- Last observed Actions run `44671272924` succeeded; live API returned `as_of=2026-11-18`, `isDemo=false`, 10 rows with `sources: ["aggregated","borsa","yahoo"]`.

## 9. Secret scan

Checked the working tree and **all 7 commits in git history** for `sb_secret_*`, `sb_publishable_*`, JWT-shaped strings, GitHub PATs, deploy-hook URLs, and committed `.env` files.

**Result: no real secret is committed in the repository or its history.** The only matches are placeholders (`sb_secret_xxxxxxxxxxxxxxxxx`, `NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...` in `.env.example`/`README.md`), variable names, and two npm `sha512` integrity hashes that happen to start with `eyJ`. The only `.env*` file ever committed, or present on disk, is `.env.example`; `.env*` is ignored by git.

Separately: the Supabase key previously exposed outside the repo (earlier in this project) has **not** been rotated yet. No value is reproduced here.

## 10. Bugs and risks (ordered by severity)

1. **Synthetic data can be published as real.** `config.py` defaults `EGX_USE_SAMPLE=true` and `analyze.yml` falls back to `'true'` when the secret is missing/empty. A missing secret silently produces 34 symbols of fake prices in `price_bars`/`recommendations` with `isDemo=false` on the dashboard.
2. **Legacy-key contract conflicts with the hard rules.** `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, README and `.env.example` still describe/disallow-allowed legacy JWT keys, while AGENTS.md forbids anon/service_role entirely. Needs a single, consistent publishable/secret naming scheme.
3. **Scheduler runs before the trading session and ignores DST.** 03:00 UTC is 05:00/06:00 Cairo; the "last update" is always the previous session. No holiday handling, so a failed/empty run can leave stale data looking current.
4. **"Stocks scanned" is wrong.** `buildStats().analyzed = rows.length` = 10 (top recommendations), while `analysis_runs.universe_size` (39) is stored but unused. The label claims "from the whole market".
5. **Win rate is structurally always "—".** `buildStats()` computes it from the current top-10 rows, but outcomes are written for *past* recommendations; the latest run's rows are never evaluated. No aggregate stats table/query exists.
6. **Silent demo fallback masks outages.** Any Supabase error or empty view result becomes fabricated `demoData()`. The badge helps, but the API payload looks authoritative.
7. **Signals carry no information.** `risk.py` thresholds (0.70 / 0.58) are hard-coded and unreachable with observed probabilities (~0.27–0.50), so all 10 rows show "مراقبة".
8. **Reward/risk is a constant** (≈1.71) for most rows because it collapses to `target_atr / stop_atr = 2.4 / 1.4`. Targets ignore EGX ±10% price limits and tick size; sub-1 EGP symbols show +22% upside.
9. **"Strength" is unexplained** (`70·probability + 20·(RR/3) + 10·momentum`), not stored explicitly, and shown as an unlabelled bar.
10. **No data quality gates.** No minimum history length, no zero/negative price checks, no impossible-jump filter; `features.py` fills NaNs with zero, so short-history symbols still get predictions.
11. **Universe is not the market.** 40 hard-coded symbols in `yahoo_provider.py`, 34 in the sample CSV; no EGX30/70/100 coverage, no liquidity filter, no penny-stock flag, no fetch/drop accounting.
12. **Provider name collision.** If `BORSA_UNIVERSE_URL`/`BORSA_HISTORY_URL` secrets are ever set, a generic `HttpProvider(name="borsa")` is appended alongside `BorsaProvider(name="borsa")`; `collected.raw_bars[...]` and `source_rows[...]` are keyed by name, so one silently overwrites the other.
13. **Potential stale cache.** `cacheLife("minutes")` on `getDashboardData()` can keep serving old rows even after the deploy hook; no explicit `revalidateTag`/`revalidatePath`.
14. **`data_source_status` loses history.** A failing run overwrites `last_success_at` with `null`, and stale rows (`sample`, `csv`) remain visible forever.
15. **No tests / no CI quality gate**, and `supabase/reset.sql` can drop all tables with no migration history or rollback path.
16. **Frontend trust gaps:** no disclaimer, methodology, tooltips, detail/history/filter/search pages, mobile layout, or Arabic company names; broad public `select` on `price_bars` and `data_source_status`.
17. **Key hygiene in `HttpProvider`:** the API key is sent simultaneously in `Authorization`, `x-api-key`, and the query string; query strings are commonly logged by proxies.
18. **Rotation still outstanding** for the key exposed outside the repository (item in §9), plus optional EGID credentials / Borsa BYOK keys for a licensed history source.

## 11. Recommended Phase 1 order

1. Remove the synthetic-data fallback from production paths (default `EGX_USE_SAMPLE=false`, fail loudly on empty data) — highest severity.
2. Resolve the key-naming contract (publishable vs secret) across code, `.env.example`, README, and Actions.
3. Fix the scheduler (post-close UTC time with an explicit DST assumption, holiday/no-new-data guard, nonzero exit on failure).
4. Move the universe to a config file with liquidity/penny filters and fetch/drop logging.
5. Derive the "stocks scanned" counter from `analysis_runs.universe_size`.
6. Add data-quality checks and minimum history before features/training.
7. Add freshness indicators and a stale-data banner to the UI.
