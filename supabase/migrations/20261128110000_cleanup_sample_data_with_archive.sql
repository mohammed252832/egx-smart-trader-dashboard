-- Applied to the live project on 2026-11-28.
-- Removes synthetic "sample" bars and everything derived from them, after copying
-- the rows into the non-exposed `archive` schema so the delete can be undone.

create schema if not exists archive;
revoke all on schema archive from public, anon, authenticated;

create table archive.sample_price_bars as
  select * from public.price_bars where source = 'sample';

-- Aggregated bars whose close equals the sample close and that have no Yahoo bar
-- for the same day were built from synthetic data.
create table archive.contaminated_aggregated_bars as
  select a.* from public.price_bars a
  where a.source = 'aggregated'
    and exists (select 1 from public.price_bars s
                where s.source = 'sample' and s.symbol = a.symbol and s.trade_date = a.trade_date
                  and abs(a.close - s.close) / nullif(s.close, 0) < 0.0001)
    and not exists (select 1 from public.price_bars y
                    where y.source = 'yahoo' and y.symbol = a.symbol and y.trade_date = a.trade_date);

-- Recommendations produced by the one run that used sample data.
create table archive.sample_recommendations as
  select * from public.recommendations where run_id = 'cee6da6b-a38a-4c51-9ac7-98d4cf86a64c';

create table archive.sample_data_source_status as
  select * from public.data_source_status where source = 'sample';

alter table archive.sample_price_bars enable row level security;
alter table archive.contaminated_aggregated_bars enable row level security;
alter table archive.sample_recommendations enable row level security;
alter table archive.sample_data_source_status enable row level security;

delete from public.recommendations where run_id = 'cee6da6b-a38a-4c51-9ac7-98d4cf86a64c';

delete from public.price_bars a
using archive.contaminated_aggregated_bars c
where a.source = 'aggregated' and a.symbol = c.symbol and a.trade_date = c.trade_date;

delete from public.price_bars where source = 'sample';
delete from public.data_source_status where source = 'sample';

-- After this migration, run the analysis workflow once so `aggregated` bars are
-- rebuilt from Yahoo for the affected symbols.
