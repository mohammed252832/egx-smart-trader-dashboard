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
    select bars.trade_date, bars.close, bars.volume
    from public.market_daily_bars as bars
    where bars.symbol = stocks.symbol
    order by bars.trade_date desc
    limit 20
  ) as recent
  group by stocks.symbol, market_session.trade_date
  having count(*) >= 20
    and max(recent.trade_date) >= market_session.trade_date - 30
    and count(recent.close) filter (where recent.close > 0) = 20
    and count(recent.volume) filter (where recent.volume > 0) >= 1
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
