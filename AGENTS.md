# AGENTS.md — EGX Smart Trader

Guidance for AI coding agents (OpenCode, etc.) working on this repo.
Read this fully before changing anything.

## 1. Project overview

EGX Smart Trader is an Arabic (RTL) dashboard that ranks Egyptian Exchange (EGX) stocks by short-term opportunity (2–3 trading sessions).

- **Frontend:** Next.js dashboard, deployed on Vercel (https://egx-smart-trader.vercel.app/). UI language is Arabic, RTL.
- **Analysis pipeline:** Python (Pandas for technical indicators, XGBoost to estimate the probability of a rise within 3 sessions). Prices are merged from more than one source.
- **Scheduler:** GitHub Actions runs the pipeline.
- **Database:** Supabase (Postgres). The pipeline writes results, the frontend reads them.
- Every recommendation has: entry, target, stop, expected upside, risk, reward/risk, strength score, signal.

The exact folder layout is not documented here. **Explore the repo first** and write down what you find (Phase 0 below) instead of assuming.

## 2. Hard rules (never break these)

1. **Never commit secrets.** No Supabase keys, tokens or `.env` files in git. Use environment variables only. If you find a secret already committed, stop, tell the user, and do not copy it anywhere.
2. **Key usage:**
   - Frontend uses only the **publishable key** (`sb_publishable_...`) via `NEXT_PUBLIC_*` env vars.
   - The **secret key** (`sb_secret_...`) is used only by the pipeline, through GitHub Actions Secrets. Never expose it to the browser, logs or the repo.
3. **Do not use or request the legacy `anon` / `service_role` JWT keys.** They were rotated and disabled.
4. **Database changes go through SQL migration files** in `supabase/migrations/` (create the folder if missing). Never modify the live DB directly. Never drop tables or delete data without asking.
5. **Work on a new git branch** (e.g. `improve/phase-1`). Small, focused commits with clear messages. No force-push, no history rewriting.
6. **Do not invent data.** No fake prices, fake success rates or placeholder statistics shown as real. If a number is not available, show "—" or an honest empty state.
7. **Ask before** large refactors, dependency swaps, framework upgrades, or deleting files.
8. Keep the UI Arabic and RTL. Keep code, comments, commit messages and docs in English unless told otherwise.

## 3. Working process

- Do the work in phases (below), **one phase at a time**. After each phase: run tests/lint/build, summarize what changed, list anything left, then wait for the user's go-ahead.
- Before editing, read the relevant code. Prefer minimal, targeted changes.
- Run the existing build/lint/tests before and after. If there are none, add basic ones for any logic you change.
- When unsure about a product decision (thresholds, signal rules), propose a default, put it in a config file, and flag it in the summary.

## 4. Known problems to fix (from the live site review, 2026-11-20)

### Data and credibility
- **"Stocks scanned" shows 10** while the label says "from the whole market". EGX has 200+ listed stocks. Either scan a real universe or show the true number honestly.
- **Data is stale:** "last update" showed 2026-11-18 while today was 2026-11-20. The scheduled pipeline is not running reliably.
- **Success rate shows "—":** there is no performance tracking, so nothing proves the model works.
- **Every signal is "مراقبة" (watch):** the signal column carries no information.
- **Targets and stops look formula-driven:** nine of ten rows have the identical reward/risk of 1.71 : 1. Some expected upsides are unrealistic (e.g. a sub-1 EGP stock showing +22% in 2–3 days).
- **"Strength" score (about 40–53) is unexplained.**

### UI and content
- No disclaimer that this is not investment advice.
- No methodology / about page, no explanation of columns.
- No per-stock detail page (chart, indicators, reason for the call).
- No filters, search or sorting.
- No history of past recommendations and outcomes.
- Stock names are English only in an Arabic UI.
- A 9-column table is probably unreadable on mobile.

## 5. Phases

### Phase 0 — Audit (no code changes)
Produce `docs/AUDIT.md` covering: folder structure, how the pipeline runs end to end, data sources, DB tables/columns in use (read from code and any migrations), how the frontend reads data, GitHub Actions workflows and their schedules, env vars needed, tests, and a list of bugs/risks you found. Do not change source code in this phase.

### Phase 1 — Reliability and honesty
1. **Universe:** move the ticker list to a config file. Cover all liquid EGX stocks (at minimum EGX30 + EGX70 + EGX100 constituents). Add a liquidity filter (minimum average daily traded value/volume, configurable) and a flag for penny stocks (price below a configurable threshold). Log how many symbols were requested, fetched successfully, and dropped (and why).
2. **Counter:** the "stocks scanned" number must come from the actual last run (stored in DB), not a constant.
3. **Scheduler:** fix the GitHub Actions workflow.
   - EGX trades Sunday–Thursday, roughly 10:00–14:30 Cairo time. Run once after the close (the cron is in UTC, so convert carefully and note the DST assumption in a comment), plus `workflow_dispatch` for manual runs.
   - Fail loudly: non-zero exit on bad/empty data, and a visible failure notification (GitHub's default email is fine).
   - Handle market holidays gracefully: do not publish duplicate or stale data as new.
4. **Freshness in the UI:** show the date/time of the last successful run and the latest market date in the data. Show a clear warning banner if the data is older than the most recent expected trading session.
5. **Data quality checks** before writing to DB: drop rows with zero/negative prices, missing OHLC, impossible jumps; require a minimum history length per symbol for indicators.

### Phase 2 — Smarter signals and risk numbers
1. Replace the fixed target/stop formula with per-stock logic, e.g. ATR-based multiples combined with recent support/resistance and volatility, so reward/risk varies by stock. Keep every multiplier and threshold in a config file.
2. Respect EGX daily price limits (±10% from previous close) and tick size when computing entry/target/stop. Cap unrealistic expected upside for a 2–3 session hold.
3. Derive the **signal** from the model probability plus risk rules, using three or more states in Arabic, for example: شراء / مراقبة / تجنّب. Thresholds go in config. Store the model probability and show it in the UI.
4. Document what "strength" means and how it is computed; show it with a tooltip in the UI.
5. Validate the model properly: time-based train/test split (no random shuffling, no look-ahead leakage), report precision/recall or hit rate at the signal thresholds, and save the report in `docs/MODEL_REPORT.md`. Add a simple backtest of the rules.

### Phase 3 — Performance tracking
1. Add a recommendations history table (migration): symbol, issue date, entry, target, stop, probability, signal, status (open / hit_target / hit_stop / expired), exit price, exit date, realized return.
2. Add an evaluator step in the pipeline: after the holding period (3 sessions) walk forward through daily high/low to decide whether target or stop was hit first, otherwise close at the third session's close. Be explicit and consistent about the rule when both are touched in one day (document the assumption).
3. Compute and store aggregate stats: win rate, average return, average win/loss, number of closed recommendations. Show them in the dashboard cards (replace the "—").
4. Add a **History** page listing past recommendations and their outcomes.

### Phase 4 — Frontend and trust
1. **Disclaimer** (Arabic) visible on every page footer and near the table: the tool is informational, not investment advice, not licensed, past performance is not a guarantee, prices may be delayed.
2. **About / Methodology page** (Arabic): data sources, indicators, model, how entry/target/stop are computed, known limits.
3. Column help/tooltips for every column.
4. **Filters and sorting:** by signal, sector, liquidity, upside, risk; search by ticker or name.
5. **Stock detail page:** price chart, key indicators (RSI, MACD, moving averages), volume, and the reasons behind the signal.
6. **Mobile:** switch the table to card layout on small screens. Check RTL alignment and numeric formatting.
7. Arabic company names alongside English (store in config or DB).
8. Nice to have: dark mode, SEO metadata and OG image, loading/empty/error states.

### Phase 5 — Security and quality
1. Verify **RLS is enabled on every table**. Public read-only policies only for tables the site needs; writes only via the secret key. Add this as migrations.
2. Add a `.env.example` listing required variables (names only, no values). Make sure `.env*` is in `.gitignore`.
3. Add tests for the indicator logic, target/stop computation, signal rules and the evaluator. Add lint/typecheck to CI.
4. Update `README.md`: setup, env vars, how to run the pipeline locally, how deployment works, how to add symbols.

## 6. Definition of done (per phase)
- Build, lint and tests pass.
- No secrets in the diff (`git diff` and a quick grep for `sb_secret`, `eyJ`, `service_role`).
- The summary lists: what changed, how to test it, assumptions made, open questions.
- Anything that needs the user (setting a GitHub Secret, running a SQL migration in Supabase, redeploying on Vercel) is listed explicitly as a manual step.

<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
