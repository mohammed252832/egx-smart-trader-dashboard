-- Applied to the live project on 2026-11-28.
-- Open sign-up gated by admin approval (profiles.status). Replaces the shared-password model.

-- Admin emails: auto-approved and flagged admin when they sign up. Edit to change admins.
create table if not exists private.admin_emails (email text primary key);
alter table private.admin_emails enable row level security;
insert into private.admin_emails (email) values ('kigobigo11@gmail.com') on conflict do nothing;

alter table public.profiles
  add column if not exists email text,
  add column if not exists status text not null default 'pending',
  add column if not exists is_admin boolean not null default false;

alter table public.profiles drop constraint if exists profiles_status_check;
alter table public.profiles add constraint profiles_status_check
  check (status in ('pending', 'approved', 'blocked'));

update public.profiles p set email = lower(u.email) from auth.users u where u.id = p.id and p.email is null;
update public.profiles p set status = 'approved'
  where exists (select 1 from private.allowed_accounts a where a.email = p.email);

-- Users may edit only their own name and alert preferences, never status or is_admin.
revoke update on public.profiles from authenticated, anon;
grant update (display_name, alert_market_summary, alert_watchlist) on public.profiles to authenticated;

create or replace function private.handle_new_user_profile()
returns trigger language plpgsql security definer set search_path = '' as $$
declare
  v_email text := lower(new.email);
  v_admin boolean := exists (select 1 from private.admin_emails where email = v_email);
  v_shared boolean := exists (select 1 from private.allowed_accounts where email = v_email);
begin
  insert into public.profiles (id, email, display_name, status, is_admin)
  values (
    new.id, v_email,
    coalesce(nullif(new.raw_user_meta_data ->> 'display_name', ''), split_part(new.email, '@', 1)),
    case when v_admin or v_shared then 'approved' else 'pending' end,
    v_admin
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

-- Sign-up is open at the Auth level; access to data is gated by approval below.
create or replace function private.enforce_allowed_auth_user()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  if coalesce(new.raw_app_meta_data ->> 'role', '') not in ('', 'member') then
    raise exception 'Dashboard accounts must use the member role' using errcode = 'check_violation';
  end if;
  return new;
end;
$$;

-- Data access: legacy shared member account OR an approved, confirmed profile.
create or replace function private.is_allowed_authenticated()
returns boolean language sql stable security definer set search_path = '' as $$
  with claims as (select auth.jwt() as jwt)
  select exists (
    select 1
    from claims
    join auth.users as u on u.id = nullif(claims.jwt ->> 'sub', '')::uuid
    join auth.sessions as s on s.user_id = u.id
      and s.id = nullif(claims.jwt ->> 'session_id', '')::uuid
    where claims.jwt ->> 'role' = 'authenticated'
      and lower(coalesce(claims.jwt ->> 'email', '')) = lower(u.email)
      and u.email_confirmed_at is not null
      and u.deleted_at is null
      and (u.banned_until is null or u.banned_until <= now())
      and (s.not_after is null or s.not_after > now())
      and (
        (
          coalesce(claims.jwt -> 'app_metadata' ->> 'role', '') = 'member'
          and coalesce(u.raw_app_meta_data ->> 'role', '') = 'member'
          and exists (select 1 from private.allowed_accounts a where a.email = lower(u.email))
        )
        or exists (select 1 from public.profiles p where p.id = u.id and p.status = 'approved')
      )
  );
$$;

create unique index if not exists watchlist_user_ticker_uidx on public.watchlist (user_id, ticker);

-- To approve a user:  update public.profiles set status = 'approved' where email = 'person@example.com';
