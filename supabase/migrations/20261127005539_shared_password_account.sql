insert into private.allowed_accounts (email)
values ('shared@egx-smart-trader.invalid')
on conflict (email) do nothing;
