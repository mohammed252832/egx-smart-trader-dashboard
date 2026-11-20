import { cacheLife } from "next/cache";
import { getSupabaseClient } from "./supabase";
import type { DashboardData, Recommendation } from "./types";

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
  confidence: number | string | null;
  signal: string;
  sources: string[] | null;
  return_pct: number | string | null;
  outcome: string | null;
};

const num = (value: number | string | null | undefined): number =>
  value === null || value === undefined ? 0 : Number(value);

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
    confidence: row.confidence === null ? null : num(row.confidence),
    signal: row.signal,
    sources: row.sources ?? [],
    return_pct: row.return_pct === null ? null : num(row.return_pct),
    outcome: row.outcome,
  };
}

function buildStats(rows: Recommendation[]): DashboardData["stats"] {
  const outcomes = rows.filter((row) => row.outcome === "win" || row.outcome === "loss");
  return {
    analyzed: rows.length,
    avgUpside: rows.length
      ? rows.reduce((sum, row) => sum + row.upside_pct, 0) / rows.length
      : 0,
    winRate: outcomes.length
      ? (outcomes.filter((row) => row.outcome === "win").length / outcomes.length) * 100
      : null,
  };
}

function demoData(): DashboardData {
  const today = new Date().toISOString().slice(0, 10);
  const rows: Recommendation[] = [
    ["ABUK", "أبو قير للأسمدة", 42.5, 46.8, 40.4, 88, 0.91, "شراء قوي"],
    ["CIB", "البنك التجاري الدولي", 78.2, 84.6, 75.1, 84, 0.88, "شراء قوي"],
    ["ARM", "أرمنت للأسمدة", 18.75, 20.4, 17.9, 79, 0.84, "شراء"],
    ["EGTS", "المصرية للاتصالات", 16.4, 17.7, 15.8, 74, 0.81, "شراء"],
    ["TALM", "طلعت المالية", 12.9, 13.9, 12.4, 71, 0.79, "شراء"],
    ["OLFI", "أوليمبيك للأسمدة", 9.85, 10.6, 9.5, 68, 0.76, "شراء"],
    ["MCFE", "المصرية للدواجن", 7.4, 7.95, 7.15, 65, 0.73, "مراقبة"],
    ["ISPH", "الإسكندرية للبتروكيماويات", 15.2, 16.3, 14.7, 62, 0.7, "مراقبة"],
    ["NWRR", "النيل للأسمدة", 5.6, 6.0, 5.42, 60, 0.68, "مراقبة"],
    ["ECAP", "الشرقية للدخان", 28.3, 30.2, 27.4, 58, 0.66, "مراقبة"],
  ].map(([symbol, name, entry, target, stop, score, confidence, signal], index) => {
    const entryPrice = Number(entry);
    const targetPrice = Number(target);
    const stopPrice = Number(stop);
    const upside = ((targetPrice - entryPrice) / entryPrice) * 100;
    const risk = ((entryPrice - stopPrice) / entryPrice) * 100;
    return {
      id: `demo-${index}`,
      symbol: String(symbol),
      name: String(name),
      as_of: today,
      horizon_days: 3,
      entry_price: entryPrice,
      target_price: targetPrice,
      stop_loss: stopPrice,
      upside_pct: upside,
      risk_pct: risk,
      reward_risk: risk ? upside / risk : 0,
      score: Number(score),
      confidence: Number(confidence),
      signal: String(signal),
      sources: ["demo"],
      return_pct: null,
      outcome: null,
    };
  });

  return {
    recommendations: rows,
    stats: buildStats(rows),
    asOf: today,
    isDemo: true,
  };
}

export async function getDashboardData(): Promise<DashboardData> {
  "use cache";
  cacheLife("minutes");

  const supabase = getSupabaseClient();
  if (!supabase) return demoData();

  const { data, error } = await supabase
    .from("top_recommendations")
    .select("*")
    .limit(10);

  if (error || !data?.length) return demoData();

  const rows = (data as RecommendationRow[]).map(toRecommendation);
  return {
    recommendations: rows,
    stats: buildStats(rows),
    asOf: rows[0]?.as_of ?? null,
    isDemo: false,
  };
}
