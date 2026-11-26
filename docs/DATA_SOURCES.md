# EGX Data Source Research — Phase 1

Date: 2026-11-25. Findings are from vendor docs, OpenAPI specs and public pages at that date.
No credentials were used and no private data was accessed. Prices/licensing can change; re-check before purchase.

## Summary

| Source | Coverage | Auth | Cost | Daily history | Live/same-day | Integration status |
| --- | --- | --- | --- | --- | --- | --- |
| Yahoo Finance `.CA` | Full public EGID list configured; history coverage varies by symbol | None (unofficial) | Free | Yes, `range=2y` | Daily bars only in free quote mode | **Active** — history backbone and daily quote fallback |
| TradingView public EGX scanner | Tested liquid EGX names, including COMI/FWRY/ABUK | None (unofficial) | Free | No history endpoint used | Delayed, configured as 15 min | **Active** — credential-free 10-minute quote refresh |
| EGID official feed | Official EGX ticker list and delayed market watch | Username/password for feed | Licensed feed | Feed has `GetSymbolHistories` | Delayed, usually 15 min | **Optional** — takes priority when credentials exist |
| Borsa (`borsa.ashh.me`) | 200+ EGX symbols, normalized, sectors | None for demo; BYOK for self-host | MIT software; demo 50 req/day | No history endpoint | Yahoo-derived quotes | **Active** — universe/sector + same-day confirmation |
| Oanor EGX API | Quotes, screener, EGX30, metadata | `x-oanor-key` | Marketplace key | No | Yes | **Configurable** via generic HTTP provider |
| EGX.news | 276 listed companies; 1-min + daily since IPO | RapidAPI key / purchased CSV | Free dev tier; CSV `$1/stock`; intraday ~`$1.50–5/day`; WSS `$1,500/mo` | Yes (paid CSV) | Yes (RapidAPI/WSS) | **Configurable** for live quotes; history is CSV delivery, not a polling API |
| Alpha Vantage / Finnhub | Vendor-dependent EGX coverage | API key | Free tiers / paid | Vendor-dependent | Vendor-dependent | Available inside self-hosted Borsa (BYOK) |
| EODHD | `EGX` exchange, active tickers + fundamentals | API key | Paid | Yes | Delayed/Live by plan | Not integrated; commercial option |
| DataCedar | No EGX in exchange registry at review time | `X-API-Key` | Free 1y daily / paid | Yes where covered | Limited | **Not suitable** unless EGX is added |
| Mubasher / Investing.com | Broad EGX market pages | Scraping / unofficial | Free web, ToS risk | Limited, unstable | Yes | Not integrated; brittle and ToS-sensitive |
| `egx` PyPI / egxpy projects | Mostly indices or downloader notebooks | Varies | Open source | Index history / downloader | Varies | Not integrated; no stable supported API |

## Source details

### 1. Yahoo Finance `.CA`
- Endpoint used: `https://query1.finance.yahoo.com/v8/finance/chart/{SYMBOL}.CA?range=2y&interval=1d`.
- Strengths: no key, real daily OHLCV, long history, good for indicators and model training.
- Weaknesses: unofficial access, rate limits (429), patchy coverage, delayed data, symbol suffixes vary.
- Decision: keep as the history backbone. Never treat its fetch time as a trade date; use the bar timestamp. Free intraday testing returned stale daily closes, so quote refreshes label Yahoo as a daily fallback rather than a live source.

### 2. TradingView public EGX scanner
- Endpoint used: `POST https://scanner.tradingview.com/egypt/scan` with `EGX:{SYMBOL}` tickers and columns for close, change, volume, OHLC, previous close and `update_time`.
- A credential-free bulk test on 2026-11-25 returned usable COMI, FWRY and ABUK quotes with source timestamps from the last EGX session.
- Strengths: one bulk request for the tracked symbols, no API key, same-day delayed prices and source timestamps.
- Weaknesses: public and unofficial endpoint, no SLA or contractual coverage, rate limits or schema changes are possible, and redistribution/commercial terms must be checked by the operator.
- Decision: use as the free 10-minute source with a configured 15-minute delay. Missing symbols are requested from the next source and reported as partial warnings; a failed scanner falls back to Yahoo daily bars. Never label these quotes real-time.

### 3. EGID (`ticker.egidegypt.com`)
- Public: `/api/Feed/GetAllMarketWatchNames` returns the official EGX symbol list (`.CA` Reuters codes, ~308 names).
- Swagger v1 lists authenticated `DelayedFeed` endpoints: `getAllMarketWatch`, `getMarketWatchForSymbolList`, `GetSymbolHistory`, `GetSymbolHistories`, `getMarketStatus`, sector/index history and market summary.
- Authentication uses `POST /api/Settings/GetToken` with `Username` and `Password`, then a Bearer token. The quote refresher uses one bulk `getAllMarketWatch` request every 10 minutes during EGX hours.
- `GetSymbolHistories` accepts `SymbolCode`, `FromDate`, `ToDate`, `Skip`, `Take`, which maps cleanly to the generic provider placeholders `{symbol}`, `{start}`, `{end}`.
- Decision: EGID is an optional official upgrade and takes priority only when both credentials are configured. TradingView is the default free intraday source, Yahoo remains the daily-history backbone, and Borsa remains metadata/cross-check only. If all quote sources fail, the dashboard keeps the last successful quotes and shows an error instead of claiming a fresh update.

### 4. Borsa
- OpenAPI: `/v1/health`, `/v1/stocks`, `/v1/quote/{symbol}`, `/v1/quotes`, `/v1/quotes/batch`, `/v1/status`.
- `/v1/stocks` returns `{count, symbols:[{symbol,name,sector}]}` with 200+ EGX names. `/v1/quotes` returns normalized `price`, `high`, `low`, `volume`, `source`, `attribution`.
- There is **no history endpoint**. Demo quotes are cached Yahoo values, so the engine binds them to Yahoo's latest trading date and sets their volume to zero to avoid double counting.
- Demo public limit: 50 requests/day globally. Self-host `ghcr.io/7ashraf/borsa:latest` with Alpha Vantage/Finnhub keys for production.
- License: MIT software; market-data licenses remain the operator's responsibility.

### 5. Oanor EGX API
- Docs: `https://www.oanor.com/docs/egx-api`; base `https://api.oanor.com/egx-api`.
- Endpoints: `/v1/quote`, `/v1/screener`, `/v1/index`, `/v1/meta`. Auth header: `x-oanor-key`.
- Quote payload includes price, change, open/high/low, volume, market cap, P/E, sector, company name and EGP currency. Screener supports top gainers/losers/most active/market cap.
- Decision: add as an optional quote source via the generic HTTP adapter (`OANOR_AUTH_HEADER=x-oanor-key`). Useful for cross-checking same-day prices, not for history.

### 6. EGX.news
- Product page: `https://egx.news/en/our-data`.
- Claims 276 listed companies; live REST/order book on RapidAPI with a free developer tier; 1-minute OHLCV CSV; full daily history since IPO/1994 sold at `$1.00` per stock.
- Index baskets: EGX30 `$1.50/day`, EGX70 `$3.00/day`, EGX100 `$4.00/day`, entire market `$5.00/day` for intraday CSV. WebSocket feed `$1,500/mo` or `$100/day`.
- Daily/intraday CSV is a purchased file delivery, not a stable polling API. Live RapidAPI is suitable for same-day quotes if a key is supplied.
- Decision: document as paid upgrade; configure via `EGXNEWS_*` generic provider with RapidAPI headers.

### 7. Commercial and community options
- **EODHD** (`eodhd.com/exchange/EGX`): active ticker list, trading hours, holidays, historical/fundamental APIs; paid.
- **DataCedar**: robust v3 bars API, but EGX was not in its exchange registry at review time; do not configure until confirmed.
- **Mubasher / Investing.com**: useful human-facing pages; scraping is ToS-sensitive and brittle.
- **egx PyPI** and **egxpy/EGX-AI-API** repositories: mostly index data, notebooks or experimental wrappers; no stable supported OHLCV API found.
- **Alpha Vantage / Finnhub**: accessible through self-hosted Borsa BYOK; coverage and EGX support must be verified per vendor account.

## Integration design in this codebase

Daily-history providers implement `Provider.fetch_universe()` and `Provider.fetch_history()`. Sources with no history of their own set `needs_trade_date=True`; the aggregator binds the latest real session date from a history provider before collecting them. This prevents a quote's fetch timestamp from being published as a market date.

The lightweight quote refresher is separate from model training. It reads the liquid `latest_market` universe, limited by `EGX_MARKET_UNIVERSE_SIZE` (default 250), and falls back to the first configured symbols before the first analysis. Provider priority is authenticated EGID when credentials exist, then TradingView delayed scanner, then Yahoo daily bars. A partial response is completed by asking the next provider only for missing symbols; each quote retains its own source, timestamp, configured delay, fetch time and market date in `live_quotes`. `data_source_status` uses `mixed` when more than one provider contributed. Partial failures are warnings; total failures preserve the last successful timestamp and prices.

Generic REST sources are configured with `{PREFIX}_UNIVERSE_URL` / `{PREFIX}_HISTORY_URL`, where `PREFIX` is one of `DATACEDAR`, `EGID`, `BORSA`, `EGX`, `OANOR`, `EGXNEWS`. Templates support `{symbol}`, `{days}`, `{start}`, `{end}`, `{api_key}`. Authentication is header-only: `{PREFIX}_AUTH_HEADER` may be a header name (`x-oanor-key`) or a template (`Authorization: Bearer {token}`), and `{PREFIX}_EXTRA_HEADERS` accepts `Header: value, Header2: value2`. API keys are never placed in query strings because proxies commonly log URLs.

Recommended stack:
1. TradingView public delayed scanner (credential-free quotes for tracked symbols, refreshed on a 10-minute schedule when GitHub Actions runs).
2. Yahoo `.CA` daily bars (history backbone and honest daily quote fallback).
3. EGID authenticated Delayed Feed when licensed (official quote priority and optional second history source).
4. Borsa self-hosted (universe/sectors, BYOK cross-check).
5. Oanor or EGX.news RapidAPI only as a licensed secondary quote cross-check.

## Legal and credibility notes

- Open-source software is not a market-data license. Check redistribution and commercial terms for every provider.
- TradingView's public scanner and Yahoo are delayed/unofficial; the dashboard must say so and must never call them real-time. GitHub Actions scheduling is best-effort and does not guarantee an update exactly every 10 minutes.
- Do not publish synthetic or placeholder prices. The sample provider is no longer wired into the production pipeline.
