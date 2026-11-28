-- Applied to the live project on 2026-11-28 (also recorded here so the repo matches the database).

-- 1) The event-trigger helper must not be callable through the REST API.
revoke execute on function public.rls_auto_enable() from public, anon, authenticated;

-- 2) Covering indexes for foreign keys.
create index if not exists recommendations_symbol_idx on public.recommendations (symbol);
create index if not exists portfolio_trades_user_id_idx on public.portfolio_trades (user_id);

-- 3) RLS initplan: evaluate auth.uid() once per query instead of once per row.
drop policy if exists "Manage own trades" on public.portfolio_trades;
create policy "Manage own trades" on public.portfolio_trades
  for all to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

drop policy if exists "Manage own watchlist" on public.watchlist;
create policy "Manage own watchlist" on public.watchlist
  for all to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);
