export type Recommendation = {
  id: string;
  symbol: string;
  name: string;
  as_of: string;
  horizon_days: number;
  entry_price: number;
  target_price: number;
  stop_loss: number;
  upside_pct: number;
  risk_pct: number;
  reward_risk: number;
  score: number;
  probability: number | null;
  confidence: number | null;
  signal: string;
  sources: string[];
  return_pct: number | null;
  outcome: string | null;
};

export type DashboardStats = {
  analyzed: number | null;
  avgUpside: number;
  winRate: number | null;
};

export type LiveQuote = {
  symbol: string;
  price: number;
  change_pct: number | null;
  source: string;
  source_timestamp: string | null;
  fetched_at: string;
  delay_seconds: number;
  market_date: string | null;
};

export type MarketRefresh = {
  source: string;
  last_success_at: string | null;
  last_error: string | null;
  rows_written: number;
  source_timestamp: string | null;
  delay_seconds: number | null;
  market_date: string | null;
  updated_at: string;
};

export type DashboardData = {
  recommendations: Recommendation[];
  stats: DashboardStats;
  asOf: string | null;
  lastRunAt: string | null;
  marketDate: string | null;
  expectedSession: string | null;
  isStale: boolean;
  isEmpty: boolean;
  liveQuotes: LiveQuote[];
  marketRefresh: MarketRefresh | null;
};
