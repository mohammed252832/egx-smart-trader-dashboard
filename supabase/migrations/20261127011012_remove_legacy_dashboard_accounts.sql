do $$
begin
  if not exists (
    select 1
    from auth.users as dashboard_user
    join private.allowed_accounts as allowed
      on allowed.email = lower(dashboard_user.email)
    where lower(dashboard_user.email) = 'shared@egx-smart-trader.invalid'
      and dashboard_user.email_confirmed_at is not null
      and dashboard_user.deleted_at is null
      and (dashboard_user.banned_until is null or dashboard_user.banned_until <= now())
      and coalesce(dashboard_user.raw_app_meta_data ->> 'role', '') = 'member'
  ) then
    raise exception 'Shared dashboard account must be configured before removing legacy accounts';
  end if;
end;
$$;

delete from private.allowed_accounts
where email in (
  'kigobigo11@wm.com',
  'mohammed.fathi2532@wm.com',
  'wael@wm.com'
);
