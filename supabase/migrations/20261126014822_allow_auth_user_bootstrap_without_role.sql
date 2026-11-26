create or replace function private.enforce_allowed_auth_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if nullif(new.email_change, '') is not null then
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

  if coalesce(new.raw_app_meta_data ->> 'role', '') not in ('', 'member') then
    raise exception 'Dashboard accounts must use the member role'
      using errcode = 'check_violation';
  end if;

  if tg_op = 'UPDATE' and coalesce(new.raw_app_meta_data ->> 'role', '') <> 'member' then
    raise exception 'Dashboard accounts must be provisioned by an administrator'
      using errcode = 'check_violation';
  end if;

  return new;
end;
$$;

revoke all on function private.enforce_allowed_auth_user() from public;
grant usage on schema private to supabase_auth_admin;
grant execute on function private.enforce_allowed_auth_user() to supabase_auth_admin;
