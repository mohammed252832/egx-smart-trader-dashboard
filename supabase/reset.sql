-- Run this ONLY if you get an error like:
--   ERROR: 42703: column "symbol" referenced in foreign key constraint does not exist
-- It removes the old/broken EGX tables so schema.sql can recreate them cleanly.
-- Warning: this deletes any existing data in these tables.

drop view if exists public.top_recommendations cascade;
drop table if exists public.recommendation_outcomes cascade;
drop table if exists public.recommendations cascade;
drop table if exists public.price_bars cascade;
drop table if exists public.analysis_runs cascade;
drop table if exists public.data_source_status cascade;
drop table if exists public.stocks cascade;
