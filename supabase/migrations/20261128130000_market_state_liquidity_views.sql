-- Applied to the live project on 2026-11-28.
-- Views behind the home page: daily liquidity, liquidity leaders, market state, liquid rising picks.
-- All are security_invoker so the RLS on the underlying tables still applies.

create or replace view public.market_liquidity_daily with (security_invoker = true) as
select
  trade_date,
  round(sum(close * volume)::numeric, 0) as total_value_egp,
  sum(volume)::bigint as total_volume,
  count(*) filter (where volume > 0)::integer as symbols_traded
from public.market_daily_bars
where close > 0
  and trade_date >= (select max(trade_date) from public.market_daily_bars) - 180
group by trade_date
order by trade_date;

create or replace view public.liquidity_leaders_latest with (security_invoker = true) as
with last_day as (select max(trade_date) as d from public.market_daily_bars),
today as (
  select b.symbol, b.trade_date, b.close, b.volume,
         (select p.close from public.market_daily_bars p
           where p.symbol = b.symbol and p.trade_date < b.trade_date
           order by p.trade_date desc limit 1) as prev_close
  from public.market_daily_bars b, last_day
  where b.trade_date = last_day.d and b.close > 0 and b.volume > 0
)
select t.symbol, s.name, s.sector, t.trade_date, t.close, t.volume,
       round((t.close * t.volume)::numeric, 0) as value_egp,
       round(((t.close - t.prev_close) / nullif(t.prev_close, 0) * 100)::numeric, 2) as change_pct,
       (rank() over (order by t.close * t.volume desc))::integer as liquidity_rank
from today t join public.stocks s on s.symbol = t.symbol
order by value_egp desc
limit 30;

-- Equal-weighted index of the 100 most liquid stocks, breadth and a trend label.
create or replace view public.market_state_daily with (security_invoker = true) as
with last_day as (select max(trade_date) as d from public.market_daily_bars),
bars as (
  select b.symbol, b.trade_date, b.close, b.volume
  from public.market_daily_bars b, last_day
  where b.trade_date >= last_day.d - 200 and b.close > 0
),
liquid as (
  select symbol from (
    select b.symbol, percentile_cont(0.5) within group (order by b.close * b.volume) as mv
    from bars b, last_day
    where b.trade_date >= last_day.d - 30 and b.volume > 0
    group by b.symbol having count(*) >= 12
  ) x order by mv desc limit 100
),
daily as (
  select b.symbol, b.trade_date, b.close, b.volume,
         lag(b.close) over w as prev_close, lag(b.trade_date) over w as prev_date
  from bars b join liquid l on l.symbol = b.symbol
  window w as (partition by b.symbol order by b.trade_date)
),
ret as (
  select trade_date, close, volume, (close / prev_close - 1) as r
  from daily
  where prev_close > 0 and trade_date - prev_date <= 5 and abs(close / prev_close - 1) <= 0.25
),
agg as (
  select trade_date,
         avg(r) as avg_ret,
         count(*)::integer as symbols,
         count(*) filter (where r > 0.0005)::integer as advancers,
         count(*) filter (where r < -0.0005)::integer as decliners,
         round(sum(close * volume)::numeric, 0) as value_traded_egp
  from ret group by trade_date
),
idx as (
  select *, 100 * exp(sum(ln(1 + avg_ret)) over (order by trade_date)) as index_value from agg
),
ma as (
  select *,
    case when count(*) over (order by trade_date rows between 4 preceding and current row) = 5
         then avg(index_value) over (order by trade_date rows between 4 preceding and current row) end as ma5,
    case when count(*) over (order by trade_date rows between 19 preceding and current row) = 20
         then avg(index_value) over (order by trade_date rows between 19 preceding and current row) end as ma20
  from idx
)
select trade_date,
       round(index_value::numeric, 2) as index_value,
       round((avg_ret * 100)::numeric, 3) as change_pct,
       round(ma5::numeric, 2) as ma5,
       round(ma20::numeric, 2) as ma20,
       advancers, decliners, symbols, value_traded_egp,
       case
         when ma20 is null then null
         when index_value > ma20 and ma5 > ma20 then 'صاعد'
         when index_value < ma20 and ma5 < ma20 then 'هابط'
         else 'متذبذب'
       end as market_state
from ma
order by trade_date;

create or replace view public.liquid_rising_picks with (security_invoker = true) as
select r.id, r.symbol, s.name, r.as_of, r.horizon_days, r.entry_price, r.target_price, r.stop_loss,
       r.upside_pct, r.risk_pct, r.reward_risk, r.score, r.probability, r.signal,
       m.liquidity_rank, m.median_daily_value_egp
from public.recommendations r
join public.stocks s on s.symbol = r.symbol
join public.latest_market m on m.symbol = r.symbol
where r.run_id = (select id from public.analysis_runs where status = 'success' order by finished_at desc limit 1)
  and r.signal in ('شراء قوي', 'شراء')
  and m.liquidity_rank <= 60
order by r.score desc
limit 10;

revoke all on public.market_liquidity_daily, public.liquidity_leaders_latest,
              public.market_state_daily, public.liquid_rising_picks from anon, public;
grant select on public.market_liquidity_daily, public.liquidity_leaders_latest,
                public.market_state_daily, public.liquid_rising_picks to authenticated;
