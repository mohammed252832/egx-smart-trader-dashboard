import { connection } from "next/server";
import { getSupabaseServerClient } from "./supabase";
import { lastExpectedTradingSession } from "./market-time";
import type { DashboardData, LiveQuote, MarketRefresh, Recommendation } from "./types";

type RecommendationRow = {
  id: string;
  symbol: string;
  name: string;
  as_of: string;
  horizon_days: number;
  entry_price: number | string;
  target_price: number | string;
  stop_loss: number | string;
  upside_pct: number | string;
  risk_pct: number | string;
  reward_risk: number | string;
  score: number | string;
  probability: number | string | null;
  confidence: number | string | null;
  signal: string;
  sources: string[] | null;
  return_pct: number | string | null;
  outcome: string | null;
};

type RunRow = {
  finished_at: string | null;
  market_date: string | null;
  universe_size: number | null;
};

type LiveQuoteRow = {
  symbol: string;
  price: number | string;
  change_pct: number | string | null;
  source: string;
  source_timestamp: string | null;
  fetched_at: string;
  delay_seconds: number | string;
  market_date: string | null;
};

type MarketRefreshRow = {
  source: string;
  last_success_at: string | null;
  last_error: string | null;
  rows_written: number | string;
  source_timestamp: string | null;
  delay_seconds: number | string | null;
  market_date: string | null;
  updated_at: string;
};

const num = (value: number | string | null | undefined): number =>
  value === null || value === undefined ? 0 : Number(value);

const nullableNum = (value: number | string | null | undefined): number | null =>
  value === null || value === undefined ? null : Number(value);

function toRecommendation(row: RecommendationRow): Recommendation {
  return {
    id: row.id,
    symbol: row.symbol,
    name: row.name,
    as_of: row.as_of,
    horizon_days: row.horizon_days,
    entry_price: num(row.entry_price),
    target_price: num(row.target_price),
    stop_loss: num(row.stop_loss),
    upside_pct: num(row.upside_pct),
    risk_pct: num(row.risk_pct),
    reward_risk: num(row.reward_risk),
    score: num(row.score),
    probability: row.probability === null ? null : num(row.probability),
    confidence: row.confidence === null ? null : num(row.confidence),
    signal: row.signal,
    sources: row.sources ?? [],
    return_pct: row.return_pct === null ? null : num(row.return_pct),
    outcome: row.outcome,
  };
}

function toLiveQuote(row: LiveQuoteRow): LiveQuote {
  return {
    symbol: row.symbol,
    price: num(row.price),
    change_pct: nullableNum(row.change_pct),
    source: row.source,
    source_timestamp: row.source_timestamp,
    fetched_at: row.fetched_at,
    delay_seconds: num(row.delay_seconds),
    market_date: row.market_date,
  };
}

function toMarketRefresh(row: MarketRefreshRow): MarketRefresh {
  return {
    source: row.source,
    last_success_at: row.last_success_at,
    last_error: row.last_error,
    rows_written: num(row.rows_written),
    source_timestamp: row.source_timestamp,
    delay_seconds: nullableNum(row.delay_seconds),
    market_date: row.market_date,
    updated_at: row.updated_at,
  };
}

function buildStats(rows: Recommendation[], analyzed: number | null): DashboardData["stats"] {
  const outcomes = rows.filter((row) => row.outcome === "win" || row.outcome === "loss");
  return {
    analyzed,
    avgUpside: rows.length
      ? rows.reduce((sum, row) => sum + row.upside_pct, 0) / rows.length
      : 0,
    winRate: outcomes.length
      ? (outcomes.filter((row) => row.outcome === "win").length / outcomes.length) * 100
      : null,
  };
}

export async function getDashboardData(): Promise<DashboardData> {
  await connection();

  const supabase = await getSupabaseServerClient();
  if (!supabase) throw new Error("Supabase is not configured");

  const [recommendationsResult, runResult, quotesResult, refreshResult] = await Promise.all([
    supabase.from("top_recommendations").select("*").limit(10),
    supabase
      .from("analysis_runs")
      .select("finished_at,market_date,universe_size")
      .eq("status", "success")
      .order("finished_at", { ascending: false })
      .limit(1),
    supabase.from("live_quotes").select("*").limit(500),
    supabase
      .from("data_source_status")
      .select("*")
      .in("source", ["egid_delayed", "tradingview_delayed", "yahoo_delayed", "mixed"])
      .order("updated_at", { ascending: false })
      .limit(1),
  ]);

  if (recommendationsResult.error || runResult.error) {
    throw new Error(`Dashboard Supabase read failed: ${recommendationsResult.error?.message ?? runResult.error?.message}`);
  }
  if (quotesResult.error || refreshResult.error) {
    console.error("Live quote refresh read failed", quotesResult.error, refreshResult.error);
  }

  const run = (runResult.data?.[0] as RunRow | undefined) ?? null;
  const rows = (recommendationsResult.data as RecommendationRow[] | null ?? []).map(toRecommendation);
  const expected = lastExpectedTradingSession();
  const marketDate = run?.market_date ?? rows[0]?.as_of ?? null;
  const refreshRow = refreshResult.data?.[0] as MarketRefreshRow | undefined;

  return {
    recommendations: rows,
    stats: buildStats(rows, run?.universe_size ?? null),
    asOf: rows[0]?.as_of ?? marketDate,
    lastRunAt: run?.finished_at ?? null,
    marketDate,
    expectedSession: expected,
    isStale: !marketDate || marketDate < expected,
    isEmpty: rows.length === 0,
    liveQuotes: ((quotesResult.data as LiveQuoteRow[] | null) ?? []).map(toLiveQuote),
    marketRefresh: refreshRow ? toMarketRefresh(refreshRow) : null,
  };
}
