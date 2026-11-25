alter table public.data_source_status
  add column if not exists source_timestamp timestamptz,
  add column if not exists delay_seconds integer,
  add column if not exists market_date date;

create table if not exists public.live_quotes (
  symbol text primary key references public.stocks (symbol) on delete cascade,
  price numeric(12, 4) not null check (price > 0),
  previous_close numeric(12, 4) check (previous_close is null or previous_close > 0),
  change_pct numeric(10, 4),
  open numeric(12, 4) check (open is null or open > 0),
  high numeric(12, 4) check (high is null or high > 0),
  low numeric(12, 4) check (low is null or low > 0),
  volume bigint not null default 0 check (volume >= 0),
  turnover numeric(18, 4) check (turnover is null or turnover >= 0),
  source text not null,
  source_timestamp timestamptz,
  delay_seconds integer not null default 900 check (delay_seconds >= 0),
  market_date date,
  fetched_at timestamptz not null default now()
);

create index if not exists live_quotes_fetched_at_idx
  on public.live_quotes (fetched_at desc);

alter table public.live_quotes enable row level security;

-- New Supabase projects may require exposing this table in Data API settings.
create policy "public read live quotes"
  on public.live_quotes for select to anon, authenticated using (true);

grant select on public.live_quotes to anon, authenticated;
