begin;

create temporary table auth_trigger_test (
  id serial primary key,
  email text not null,
  email_change text,
  raw_app_meta_data jsonb not null default '{}'::jsonb
) on commit drop;

create trigger auth_trigger_test_guard
  before insert or update on auth_trigger_test
  for each row execute function private.enforce_allowed_auth_user();

do $$
begin
  insert into auth_trigger_test (email, email_change, raw_app_meta_data)
  values ('shared@egx-smart-trader.invalid', '', '{"role":"member"}'::jsonb);

  update auth_trigger_test
  set raw_app_meta_data = '{}'::jsonb
  where email = 'shared@egx-smart-trader.invalid';

  update auth_trigger_test
  set raw_app_meta_data = '{"role":"member"}'::jsonb
  where email = 'shared@egx-smart-trader.invalid';

  begin
    insert into auth_trigger_test (email, email_change, raw_app_meta_data)
    values ('shared@egx-smart-trader.invalid', 'replacement@example.com', '{"role":"member"}'::jsonb);
    raise exception 'Expected a pending email change to be rejected';
  exception when check_violation then
    null;
  end;

  begin
    insert into auth_trigger_test (email, email_change, raw_app_meta_data)
    values ('outsider@example.com', '', '{"role":"member"}'::jsonb);
    raise exception 'Expected a non-allowlisted account to be rejected';
  exception when check_violation then
    null;
  end;

  begin
    insert into auth_trigger_test (email, email_change, raw_app_meta_data)
    values ('shared@egx-smart-trader.invalid', '', '{"role":"admin"}'::jsonb);
    raise exception 'Expected a non-member role to be rejected';
  exception when check_violation then
    null;
  end;

  begin
    update auth_trigger_test
    set raw_app_meta_data = '{}'::jsonb
    where email = 'shared@egx-smart-trader.invalid';
    raise exception 'Expected an update without the member role to be rejected';
  exception when check_violation then
    null;
  end;

  begin
    update auth_trigger_test
    set email = 'replacement@example.com'
    where email = 'shared@egx-smart-trader.invalid';
    raise exception 'Expected an email reassignment to be rejected';
  exception when check_violation then
    null;
  end;

  if (select count(*) from auth_trigger_test) <> 1 then
    raise exception 'Unexpected number of accepted auth trigger test rows';
  end if;
end;
$$;

select 'auth trigger regression checks passed' as result;

rollback;
