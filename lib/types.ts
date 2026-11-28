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

export type MarketStock = {
  symbol: string;
  name: string;
  sector: string | null;
  liquidity_rank: number;
  liquidity_sessions: number;
  median_daily_value_egp: number;
  price: number;
  previous_close: number | null;
  change_pct: number | null;
  open: number | null;
  high: number | null;
  low: number | null;
  volume: number;
  turnover: number | null;
  effective_market_date: string | null;
  price_origin: "live_quote" | "daily_close";
  source: string;
  source_timestamp: string | null;
  delay_seconds: number;
  fetched_at: string | null;
};

export type MonthlyBar = {
  month_start: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  sessions: number;
  first_trade_date: string;
  last_trade_date: string;
  sources: string[];
};

export type StockChartData = {
  symbol: string;
  name: string;
  sector: string | null;
  bars: MonthlyBar[];
};

export type MarketState = "صاعد" | "هابط" | "متذبذب";

export type MarketStatePoint = {
  trade_date: string;
  index_value: number;
  change_pct: number;
  ma5: number | null;
  ma20: number | null;
  advancers: number;
  decliners: number;
  symbols: number;
  value_traded_egp: number;
  market_state: MarketState | null;
};

export type LiquidityDay = {
  trade_date: string;
  total_value_egp: number;
  total_volume: number;
  symbols_traded: number;
};

export type LiquidityLeader = {
  symbol: string;
  name: string;
  sector: string | null;
  trade_date: string;
  close: number;
  volume: number;
  value_egp: number;
  change_pct: number | null;
  liquidity_rank: number;
};

export type LiquidRisingPick = {
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
  signal: string;
  liquidity_rank: number;
  median_daily_value_egp: number;
};
