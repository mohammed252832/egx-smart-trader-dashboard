-- Regression checks for private.enforce_allowed_auth_user() after open sign-up
-- (migration 20261128120000_signup_with_approval.sql). Run in the SQL editor; it rolls back.
begin;

create temporary table auth_trigger_test (
  id serial primary key,
  email text not null,
  raw_app_meta_data jsonb not null default '{}'::jsonb
) on commit drop;

create trigger auth_trigger_test_guard
  before insert or update on auth_trigger_test
  for each row execute function private.enforce_allowed_auth_user();

do $$
begin
  -- Anyone may sign up (access is gated by profiles.status, not by this trigger).
  insert into auth_trigger_test (email) values ('new.user@example.com');
  insert into auth_trigger_test (email, raw_app_meta_data)
  values ('member@example.com', '{"role":"member"}'::jsonb);

  update auth_trigger_test set email = 'renamed@example.com' where email = 'new.user@example.com';

  -- But no account may carry a role other than "member".
  begin
    insert into auth_trigger_test (email, raw_app_meta_data)
    values ('admin@example.com', '{"role":"admin"}'::jsonb);
    raise exception 'Expected a non-member role to be rejected';
  exception when check_violation then
    null;
  end;

  if (select count(*) from auth_trigger_test) <> 2 then
    raise exception 'Unexpected number of accepted auth trigger test rows';
  end if;
end;
$$;

select 'auth trigger regression checks passed' as result;

rollback;
