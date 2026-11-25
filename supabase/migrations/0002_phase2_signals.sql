-- Phase 2 signal transparency. Safe to re-run.
-- Stores the raw model probability separately from the legacy confidence column.

alter table public.recommendations
  add column if not exists probability numeric(8, 4);

update public.recommendations
  set probability = confidence
  where probability is null and confidence is not null;

-- Drop and recreate because CREATE OR REPLACE VIEW cannot rename/reorder
-- existing view columns (e.g. inserting probability before confidence).
drop view if exists public.top_recommendations;

create view public.top_recommendations
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
  r.probability,
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

grant select on public.top_recommendations to anon, authenticated;
