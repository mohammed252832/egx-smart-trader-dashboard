import "server-only";

import { connection } from "next/server";
import { getSupabaseServerClient } from "./supabase";
import type {
  LiquidityDay,
  LiquidityLeader,
  LiquidRisingPick,
  MarketState,
  MarketStatePoint,
} from "./types";

type Numeric = number | string | null;

const num = (value: Numeric | undefined): number => (value === null || value === undefined ? 0 : Number(value));
const nullableNum = (value: Numeric | undefined): number | null =>
  value === null || value === undefined ? null : Number(value);

function toState(value: unknown): MarketState | null {
  return value === "صاعد" || value === "هابط" || value === "متذبذب" ? value : null;
}

export type Insights = {
  marketState: MarketStatePoint[];
  liquidityDays: LiquidityDay[];
  leaders: LiquidityLeader[];
  risingPicks: LiquidRisingPick[];
  /** Section names whose query failed, so the page can say so instead of showing blanks. */
  failed: string[];
};

/** Market-wide views used by the home page. A failed query degrades only its own section. */
export async function getInsights(): Promise<Insights> {
  await connection();
  const supabase = await getSupabaseServerClient();
  if (!supabase) throw new Error("Supabase is not configured");

  const [stateResult, liquidityResult, leadersResult, picksResult] = await Promise.all([
    supabase.from("market_state_daily").select("*").order("trade_date", { ascending: false }).limit(90),
    supabase.from("market_liquidity_daily").select("*").order("trade_date", { ascending: false }).limit(30),
    supabase.from("liquidity_leaders_latest").select("*").order("liquidity_rank", { ascending: true }).limit(15),
    supabase.from("liquid_rising_picks").select("*").order("score", { ascending: false }).limit(10),
  ]);

  const failed: string[] = [];
  if (stateResult.error) failed.push("market_state");
  if (liquidityResult.error) failed.push("liquidity");
  if (leadersResult.error) failed.push("leaders");
  if (picksResult.error) failed.push("rising_picks");
  for (const result of [stateResult, liquidityResult, leadersResult, picksResult]) {
    if (result.error) console.error("Insights read failed", result.error.message);
  }

  type StateRow = Record<string, Numeric | string>;
  const marketState = ((stateResult.data as StateRow[] | null) ?? [])
    .map((row): MarketStatePoint => ({
      trade_date: String(row.trade_date),
      index_value: num(row.index_value as Numeric),
      change_pct: num(row.change_pct as Numeric),
      ma5: nullableNum(row.ma5 as Numeric),
      ma20: nullableNum(row.ma20 as Numeric),
      advancers: num(row.advancers as Numeric),
      decliners: num(row.decliners as Numeric),
      symbols: num(row.symbols as Numeric),
      value_traded_egp: num(row.value_traded_egp as Numeric),
      market_state: toState(row.market_state),
    }))
    .reverse();

  const liquidityDays = ((liquidityResult.data as StateRow[] | null) ?? [])
    .map((row): LiquidityDay => ({
      trade_date: String(row.trade_date),
      total_value_egp: num(row.total_value_egp as Numeric),
      total_volume: num(row.total_volume as Numeric),
      symbols_traded: num(row.symbols_traded as Numeric),
    }))
    .reverse();

  const leaders = ((leadersResult.data as StateRow[] | null) ?? []).map((row): LiquidityLeader => ({
    symbol: String(row.symbol),
    name: String(row.name),
    sector: row.sector === null || row.sector === undefined ? null : String(row.sector),
    trade_date: String(row.trade_date),
    close: num(row.close as Numeric),
    volume: num(row.volume as Numeric),
    value_egp: num(row.value_egp as Numeric),
    change_pct: nullableNum(row.change_pct as Numeric),
    liquidity_rank: num(row.liquidity_rank as Numeric),
  }));

  const risingPicks = ((picksResult.data as StateRow[] | null) ?? []).map((row): LiquidRisingPick => ({
    id: String(row.id),
    symbol: String(row.symbol),
    name: String(row.name),
    as_of: String(row.as_of),
    horizon_days: num(row.horizon_days as Numeric),
    entry_price: num(row.entry_price as Numeric),
    target_price: num(row.target_price as Numeric),
    stop_loss: num(row.stop_loss as Numeric),
    upside_pct: num(row.upside_pct as Numeric),
    risk_pct: num(row.risk_pct as Numeric),
    reward_risk: num(row.reward_risk as Numeric),
    score: num(row.score as Numeric),
    probability: nullableNum(row.probability as Numeric),
    signal: String(row.signal),
    liquidity_rank: num(row.liquidity_rank as Numeric),
    median_daily_value_egp: num(row.median_daily_value_egp as Numeric),
  }));

  return { marketState, liquidityDays, leaders, risingPicks, failed };
}
