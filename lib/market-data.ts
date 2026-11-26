import "server-only";

import { connection } from "next/server";
import { getSupabaseServerClient } from "./supabase";
import type { MarketStock, MonthlyBar, StockChartData } from "./types";

type MarketRow = {
  symbol: string;
  name: string;
  sector: string | null;
  liquidity_rank: number | string;
  liquidity_sessions: number | string;
  median_daily_value_egp: number | string;
  price: number | string;
  previous_close: number | string | null;
  change_pct: number | string | null;
  open: number | string | null;
  high: number | string | null;
  low: number | string | null;
  volume: number | string;
  turnover: number | string | null;
  effective_market_date: string | null;
  price_origin: "live_quote" | "daily_close";
  source: string;
  source_timestamp: string | null;
  delay_seconds: number | string;
  fetched_at: string | null;
};

type MonthlyRow = {
  month_start: string;
  open: number | string;
  high: number | string;
  low: number | string;
  close: number | string;
  volume: number | string;
  sessions: number | string;
  first_trade_date: string;
  last_trade_date: string;
  sources: string[] | null;
};

const num = (value: number | string): number => Number(value);
const nullableNum = (value: number | string | null): number | null =>
  value === null ? null : Number(value);

function toMarketStock(row: MarketRow): MarketStock {
  return {
    symbol: row.symbol,
    name: row.name,
    sector: row.sector,
    liquidity_rank: num(row.liquidity_rank),
    liquidity_sessions: num(row.liquidity_sessions),
    median_daily_value_egp: num(row.median_daily_value_egp),
    price: num(row.price),
    previous_close: nullableNum(row.previous_close),
    change_pct: nullableNum(row.change_pct),
    open: nullableNum(row.open),
    high: nullableNum(row.high),
    low: nullableNum(row.low),
    volume: num(row.volume),
    turnover: nullableNum(row.turnover),
    effective_market_date: row.effective_market_date,
    price_origin: row.price_origin,
    source: row.source,
    source_timestamp: row.source_timestamp,
    delay_seconds: num(row.delay_seconds),
    fetched_at: row.fetched_at,
  };
}

function toMonthlyBar(row: MonthlyRow): MonthlyBar {
  return {
    month_start: row.month_start,
    open: num(row.open),
    high: num(row.high),
    low: num(row.low),
    close: num(row.close),
    volume: num(row.volume),
    sessions: num(row.sessions),
    first_trade_date: row.first_trade_date,
    last_trade_date: row.last_trade_date,
    sources: row.sources ?? [],
  };
}

export async function getLatestMarket(limit = 250): Promise<MarketStock[]> {
  await connection();
  const supabase = await getSupabaseServerClient();
  if (!supabase) throw new Error("Supabase is not configured");

  const { data, error } = await supabase
    .from("latest_market")
    .select("*")
    .order("liquidity_rank", { ascending: true })
    .limit(Math.max(1, Math.min(500, limit)));

  if (error) throw new Error(`Latest market Supabase read failed: ${error.message}`);
  return ((data as MarketRow[] | null) ?? []).map(toMarketStock);
}

export async function getStockChartData(symbol: string): Promise<StockChartData | null> {
  await connection();
  const normalized = symbol.trim().toUpperCase();
  if (!/^[A-Z0-9]{1,12}$/.test(normalized)) return null;

  const supabase = await getSupabaseServerClient();
  if (!supabase) throw new Error("Supabase is not configured");

  const [barsResult, stockResult] = await Promise.all([
    supabase
      .from("monthly_price_bars")
      .select("*")
      .eq("symbol", normalized)
      .order("month_start", { ascending: false })
      .limit(36),
    supabase.from("stocks").select("name,sector").eq("symbol", normalized).limit(1),
  ]);

  if (barsResult.error || stockResult.error) {
    throw new Error(`Monthly chart Supabase read failed: ${barsResult.error?.message ?? stockResult.error?.message}`);
  }

  const stock = stockResult.data?.[0] as { name: string; sector: string | null } | undefined;
  const bars = ((barsResult.data as MonthlyRow[] | null) ?? []).map(toMonthlyBar).reverse();
  return {
    symbol: normalized,
    name: stock?.name ?? normalized,
    sector: stock?.sector ?? null,
    bars,
  };
}
