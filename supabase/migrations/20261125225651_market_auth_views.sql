create schema if not exists private;
revoke all on schema private from public;
revoke all on schema private from anon, authenticated;

create table if not exists private.allowed_accounts (
  email text primary key check (email = lower(email))
);
alter table private.allowed_accounts enable row level security;

insert into private.allowed_accounts (email)
values
  ('kigobigo11@wm.com'),
  ('mohammed.fathi2532@wm.com'),
  ('wael@wm.com')
on conflict (email) do nothing;

create or replace function private.is_allowed_authenticated()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  with claims as (
    select auth.jwt() as jwt
  )
  select exists (
    select 1
    from claims
    join auth.users as dashboard_user
      on dashboard_user.id = nullif(claims.jwt ->> 'sub', '')::uuid
    join auth.sessions as dashboard_session
      on dashboard_session.user_id = dashboard_user.id
      and dashboard_session.id = nullif(claims.jwt ->> 'session_id', '')::uuid
    join private.allowed_accounts as allowed
      on allowed.email = lower(dashboard_user.email)
    where claims.jwt ->> 'role' = 'authenticated'
      and coalesce(claims.jwt -> 'app_metadata' ->> 'role', '') = 'member'
      and coalesce(dashboard_user.raw_app_meta_data ->> 'role', '') = 'member'
      and lower(coalesce(claims.jwt ->> 'email', '')) = lower(dashboard_user.email)
      and dashboard_user.email_confirmed_at is not null
      and dashboard_user.deleted_at is null
      and (dashboard_user.banned_until is null or dashboard_user.banned_until <= now())
      and (dashboard_session.not_after is null or dashboard_session.not_after > now())
  );
$$;

revoke all on function private.is_allowed_authenticated() from public;
grant usage on schema private to authenticated;
grant execute on function private.is_allowed_authenticated() to authenticated;

create or replace function private.enforce_allowed_auth_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if new.email_change is not null then
    raise exception 'Email changes are disabled for dashboard accounts'
      using errcode = 'check_violation';
  end if;

  if tg_op = 'UPDATE' and new.email is distinct from old.email then
    raise exception 'Email changes are disabled for dashboard accounts'
      using errcode = 'check_violation';
  end if;

  if not exists (
    select 1
    from private.allowed_accounts
    where email = lower(new.email)
  ) then
    raise exception 'This email is not allowed to create a dashboard account'
      using errcode = 'check_violation';
  end if;

  if coalesce(new.raw_app_meta_data ->> 'role', '') <> 'member' then
    raise exception 'Dashboard accounts must be provisioned by an administrator'
      using errcode = 'check_violation';
  end if;

  return new;
end;
$$;

revoke all on function private.enforce_allowed_auth_user() from public;
grant usage on schema private to supabase_auth_admin;
grant execute on function private.enforce_allowed_auth_user() to supabase_auth_admin;

drop trigger if exists enforce_allowed_dashboard_user on auth.users;
create trigger enforce_allowed_dashboard_user
  before insert or update on auth.users
  for each row execute function private.enforce_allowed_auth_user();

create index if not exists price_bars_market_symbol_date_idx
  on public.price_bars (symbol, trade_date desc)
  where source in ('aggregated', 'yahoo');

create or replace view public.market_daily_bars
  with (security_invoker = true)
as
select distinct on (bars.symbol, bars.trade_date)
  bars.symbol,
  bars.trade_date,
  bars.open,
  bars.high,
  bars.low,
  bars.close,
  bars.volume,
  bars.source
from public.price_bars as bars
where bars.source in ('aggregated', 'yahoo')
order by
  bars.symbol,
  bars.trade_date,
  case bars.source when 'aggregated' then 0 else 1 end;

create or replace view public.latest_market
  with (security_invoker = true)
as
with market_session as (
  select max(trade_date) as trade_date
  from public.market_daily_bars
), liquidity as (
  select
    stocks.symbol,
    count(*)::integer as liquidity_sessions,
    percentile_cont(0.5) within group (order by recent.close * recent.volume)
      filter (where recent.close > 0 and recent.volume > 0) as median_daily_value_egp
  from public.stocks as stocks
  cross join market_session
  cross join lateral (
    select bars.close, bars.volume
    from public.market_daily_bars as bars
    where bars.symbol = stocks.symbol
    order by bars.trade_date desc
    limit 20
  ) as recent
  where stocks.is_active
    and exists (
      select 1
      from public.market_daily_bars as current_bar
      where current_bar.symbol = stocks.symbol
        and current_bar.trade_date = market_session.trade_date
    )
  group by stocks.symbol
  having count(*) >= 20
    and count(recent.close) filter (where recent.close > 0 and recent.volume > 0) = 20
), ranked as (
  select
    stocks.symbol,
    stocks.name,
    stocks.sector,
    liquidity.liquidity_sessions,
    round(liquidity.median_daily_value_egp::numeric, 2) as median_daily_value_egp,
    row_number() over (
      order by liquidity.median_daily_value_egp desc, stocks.symbol
    ) as liquidity_rank
  from public.stocks as stocks
  join liquidity on liquidity.symbol = stocks.symbol
)
select
  ranked.symbol,
  ranked.name,
  ranked.sector,
  ranked.liquidity_rank,
  ranked.liquidity_sessions,
  ranked.median_daily_value_egp,
  daily.trade_date as daily_trade_date,
  previous.close as daily_previous_close,
  daily.open as daily_open,
  daily.high as daily_high,
  daily.low as daily_low,
  daily.close as daily_close,
  daily.volume as daily_volume,
  quote.price as quote_price,
  quote.previous_close as quote_previous_close,
  quote.change_pct as quote_change_pct,
  quote.open as quote_open,
  quote.high as quote_high,
  quote.low as quote_low,
  quote.volume as quote_volume,
  quote.turnover as quote_turnover,
  quote.source as quote_source,
  quote.source_timestamp as quote_source_timestamp,
  quote.delay_seconds as quote_delay_seconds,
  quote.market_date as quote_market_date,
  quote.fetched_at as quote_fetched_at,
  case
    when quote.market_date is not null and quote.market_date > daily.trade_date then quote.price
    else daily.close
  end as price,
  case
    when quote.market_date is not null and quote.market_date > daily.trade_date then quote.previous_close
    else previous.close
  end as previous_close,
  case
    when quote.market_date is not null and quote.market_date > daily.trade_date then quote.change_pct
    when previous.close is null or previous.close = 0 then null
    else round(((daily.close - previous.close) / previous.close * 100)::numeric, 4)
  end as change_pct,
  case
    when quote.market_date is not null and quote.market_date > daily.trade_date then quote.open
    else daily.open
  end as open,
  case
    when quote.market_date is not null and quote.market_date > daily.trade_date then quote.high
    else daily.high
  end as high,
  case
    when quote.market_date is not null and quote.market_date > daily.trade_date then quote.low
    else daily.low
  end as low,
  case
    when quote.market_date is not null and quote.market_date > daily.trade_date then quote.volume
    else daily.volume
  end as volume,
  case
    when quote.market_date is not null and quote.market_date > daily.trade_date then quote.turnover
    else null
  end as turnover,
  case
    when quote.market_date is not null and quote.market_date > daily.trade_date then quote.market_date
    else daily.trade_date
  end as effective_market_date,
  case
    when quote.market_date is not null and quote.market_date > daily.trade_date then 'live_quote'
    else 'daily_close'
  end as price_origin,
  case
    when quote.market_date is not null and quote.market_date > daily.trade_date then quote.source
    else 'daily_close'
  end as source,
  case
    when quote.market_date is not null and quote.market_date > daily.trade_date then quote.source_timestamp
    else null
  end as source_timestamp,
  case
    when quote.market_date is not null and quote.market_date > daily.trade_date then quote.delay_seconds
    else 86400
  end as delay_seconds,
  case
    when quote.market_date is not null and quote.market_date > daily.trade_date then quote.fetched_at
    else null
  end as fetched_at
from ranked
left join lateral (
  select bars.*
  from public.market_daily_bars as bars
  where bars.symbol = ranked.symbol
  order by bars.trade_date desc
  limit 1
) as daily on true
left join lateral (
  select bars.close
  from public.market_daily_bars as bars
  where bars.symbol = ranked.symbol
  order by bars.trade_date desc
  offset 1
  limit 1
) as previous on true
left join public.live_quotes as quote on quote.symbol = ranked.symbol;

create or replace view public.monthly_price_bars
  with (security_invoker = true)
as
select
  bars.symbol,
  date_trunc('month', bars.trade_date)::date as month_start,
  (array_agg(bars.open order by bars.trade_date))[1] as open,
  max(bars.high) as high,
  min(bars.low) as low,
  (array_agg(bars.close order by bars.trade_date desc))[1] as close,
  sum(bars.volume) as volume,
  count(*)::integer as sessions,
  min(bars.trade_date) as first_trade_date,
  max(bars.trade_date) as last_trade_date,
  array_agg(distinct bars.source order by bars.source) as sources
from public.market_daily_bars as bars
group by bars.symbol, date_trunc('month', bars.trade_date);

drop policy if exists "public read stocks" on public.stocks;
drop policy if exists "public read price bars" on public.price_bars;
drop policy if exists "public read analysis runs" on public.analysis_runs;
drop policy if exists "public read recommendations" on public.recommendations;
drop policy if exists "public read outcomes" on public.recommendation_outcomes;
drop policy if exists "public read source status" on public.data_source_status;
drop policy if exists "public read live quotes" on public.live_quotes;

revoke all on public.stocks from anon, authenticated;
revoke all on public.price_bars from anon, authenticated;
revoke all on public.analysis_runs from anon, authenticated;
revoke all on public.recommendations from anon, authenticated;
revoke all on public.recommendation_outcomes from anon, authenticated;
revoke all on public.data_source_status from anon, authenticated;
revoke all on public.live_quotes from anon, authenticated;

grant select on public.stocks to authenticated;
grant select on public.price_bars to authenticated;
grant select on public.analysis_runs to authenticated;
grant select on public.recommendations to authenticated;
grant select on public.recommendation_outcomes to authenticated;
grant select on public.data_source_status to authenticated;
grant select on public.live_quotes to authenticated;

drop policy if exists "authenticated read stocks" on public.stocks;
drop policy if exists "authenticated read price bars" on public.price_bars;
drop policy if exists "authenticated read analysis runs" on public.analysis_runs;
drop policy if exists "authenticated read recommendations" on public.recommendations;
drop policy if exists "authenticated read outcomes" on public.recommendation_outcomes;
drop policy if exists "authenticated read source status" on public.data_source_status;
drop policy if exists "authenticated read live quotes" on public.live_quotes;

create policy "authenticated read stocks"
  on public.stocks for select to authenticated
  using ((select private.is_allowed_authenticated()));
create policy "authenticated read price bars"
  on public.price_bars for select to authenticated
  using ((select private.is_allowed_authenticated()));
create policy "authenticated read analysis runs"
  on public.analysis_runs for select to authenticated
  using ((select private.is_allowed_authenticated()));
create policy "authenticated read recommendations"
  on public.recommendations for select to authenticated
  using ((select private.is_allowed_authenticated()));
create policy "authenticated read outcomes"
  on public.recommendation_outcomes for select to authenticated
  using ((select private.is_allowed_authenticated()));
create policy "authenticated read source status"
  on public.data_source_status for select to authenticated
  using ((select private.is_allowed_authenticated()));
create policy "authenticated read live quotes"
  on public.live_quotes for select to authenticated
  using ((select private.is_allowed_authenticated()));

revoke all on public.top_recommendations from anon, authenticated;
revoke all on public.market_daily_bars from anon, authenticated;
revoke all on public.latest_market from anon, authenticated;
revoke all on public.monthly_price_bars from anon, authenticated;

grant select on public.top_recommendations to authenticated;
grant select on public.market_daily_bars to authenticated;
grant select on public.latest_market to authenticated;
grant select on public.monthly_price_bars to authenticated;
