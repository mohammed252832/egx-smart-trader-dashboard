create extension if not exists pgcrypto;

create table if not exists public.stocks (
  symbol text primary key,
  name text not null,
  sector text,
  is_active boolean not null default true,
  updated_at timestamptz not null default now()
);

create table if not exists public.price_bars (
  symbol text not null references public.stocks (symbol) on delete cascade,
  trade_date date not null,
  open numeric(12, 4),
  high numeric(12, 4),
  low numeric(12, 4),
  close numeric(12, 4) not null,
  volume bigint,
  source text not null,
  adjusted boolean not null default false,
  updated_at timestamptz not null default now(),
  primary key (symbol, trade_date, source)
);

create index if not exists price_bars_symbol_date_idx
  on public.price_bars (symbol, trade_date desc);

create table if not exists public.analysis_runs (
  id uuid primary key default gen_random_uuid(),
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  status text not null check (status in ('running', 'success', 'failed')),
  model_version text,
  universe_size integer,
  notes text
);

create table if not exists public.recommendations (
  id uuid primary key default gen_random_uuid(),
  run_id uuid references public.analysis_runs (id) on delete cascade,
  symbol text not null references public.stocks (symbol),
  as_of date not null,
  horizon_days smallint not null default 3,
  entry_price numeric(12, 4) not null,
  target_price numeric(12, 4) not null,
  stop_loss numeric(12, 4) not null,
  upside_pct numeric(8, 4) not null,
  risk_pct numeric(8, 4) not null,
  reward_risk numeric(8, 4) not null,
  score numeric(8, 4) not null,
  confidence numeric(8, 4),
  signal text not null,
  sources text[] not null default '{}',
  created_at timestamptz not null default now(),
  unique (run_id, symbol)
);

create index if not exists recommendations_as_of_score_idx
  on public.recommendations (as_of desc, score desc);

create table if not exists public.recommendation_outcomes (
  recommendation_id uuid primary key
    references public.recommendations (id) on delete cascade,
  evaluated_at timestamptz not null default now(),
  exit_date date not null,
  exit_price numeric(12, 4) not null,
  max_high numeric(12, 4),
  min_low numeric(12, 4),
  hit_target boolean not null default false,
  hit_stop boolean not null default false,
  return_pct numeric(8, 4) not null,
  outcome text not null check (outcome in ('win', 'loss', 'open', 'flat'))
);

create table if not exists public.data_source_status (
  source text primary key,
  last_success_at timestamptz,
  last_error text,
  rows_written integer not null default 0,
  updated_at timestamptz not null default now()
);

create or replace view public.top_recommendations
  with (security_invoker = true)
as
select
  r.id,
  r.symbol,
  s.name,
  r.as_of,
  r.horizon_days,
  r.entry_price,
  r.target_price,
  r.stop_loss,
  r.upside_pct,
  r.risk_pct,
  r.reward_risk,
  r.score,
  r.confidence,
  r.signal,
  r.sources,
  o.return_pct,
  o.outcome
from public.recommendations as r
join public.stocks as s on s.symbol = r.symbol
left join public.recommendation_outcomes as o
  on o.recommendation_id = r.id
where r.run_id = (
  select id from public.analysis_runs
  where status = 'success'
  order by finished_at desc
  limit 1
)
order by r.score desc
limit 10;

alter table public.stocks enable row level security;
alter table public.price_bars enable row level security;
alter table public.analysis_runs enable row level security;
alter table public.recommendations enable row level security;
alter table public.recommendation_outcomes enable row level security;
alter table public.data_source_status enable row level security;

create policy "public read stocks"
  on public.stocks for select to anon, authenticated using (true);

create policy "public read price bars"
  on public.price_bars for select to anon, authenticated using (true);

create policy "public read analysis runs"
  on public.analysis_runs for select to anon, authenticated using (true);

create policy "public read recommendations"
  on public.recommendations for select to anon, authenticated using (true);

create policy "public read outcomes"
  on public.recommendation_outcomes for select to anon, authenticated using (true);

create policy "public read source status"
  on public.data_source_status for select to anon, authenticated using (true);

grant select on public.top_recommendations to anon, authenticated;
