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
  values ('kigobigo11@wm.com', '', '{"role":"member"}'::jsonb);

  insert into auth_trigger_test (email, email_change, raw_app_meta_data)
  values ('mohammed.fathi2532@wm.com', null, '{"role":"member"}'::jsonb);

  insert into auth_trigger_test (email, email_change, raw_app_meta_data)
  values ('wael@wm.com', '', '{}'::jsonb);

  update auth_trigger_test
  set raw_app_meta_data = '{}'::jsonb
  where email = 'wael@wm.com';

  update auth_trigger_test
  set raw_app_meta_data = '{"role":"member"}'::jsonb
  where email = 'wael@wm.com';

  begin
    insert into auth_trigger_test (email, email_change, raw_app_meta_data)
    values ('wael@wm.com', 'replacement@example.com', '{"role":"member"}'::jsonb);
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
    values ('wael@wm.com', '', '{"role":"admin"}'::jsonb);
    raise exception 'Expected a non-member role to be rejected';
  exception when check_violation then
    null;
  end;

  begin
    update auth_trigger_test
    set raw_app_meta_data = '{}'::jsonb
    where email = 'kigobigo11@wm.com';
    raise exception 'Expected an update without the member role to be rejected';
  exception when check_violation then
    null;
  end;

  begin
    update auth_trigger_test
    set email = 'wael@wm.com'
    where email = 'kigobigo11@wm.com';
    raise exception 'Expected an email reassignment to be rejected';
  exception when check_violation then
    null;
  end;

  if (select count(*) from auth_trigger_test) <> 3 then
    raise exception 'Unexpected number of accepted auth trigger test rows';
  end if;
end;
$$;

select 'auth trigger regression checks passed' as result;

rollback;
