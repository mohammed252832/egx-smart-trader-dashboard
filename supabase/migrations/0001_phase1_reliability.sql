-- Phase 1 reliability metadata. Safe to re-run.
-- Adds run-level counters used by the dashboard and by the stale/holiday guard.

alter table public.analysis_runs
  add column if not exists market_date date,
  add column if not exists symbols_requested integer,
  add column if not exists symbols_fetched integer,
  add column if not exists symbols_eligible integer,
  add column if not exists symbols_dropped integer,
  add column if not exists drop_reasons jsonb not null default '{}'::jsonb,
  add column if not exists quality_report jsonb not null default '{}'::jsonb;

alter table public.analysis_runs drop constraint if exists analysis_runs_status_check;
alter table public.analysis_runs
  add constraint analysis_runs_status_check
  check (status in ('running', 'success', 'failed', 'skipped'));

create index if not exists analysis_runs_status_finished_idx
  on public.analysis_runs (status, finished_at desc);
