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
  confidence: number | null;
  signal: string;
  sources: string[];
  return_pct: number | null;
  outcome: string | null;
};

export type DashboardStats = {
  analyzed: number;
  avgUpside: number;
  winRate: number | null;
};

export type DashboardData = {
  recommendations: Recommendation[];
  stats: DashboardStats;
  asOf: string | null;
  isDemo: boolean;
};
