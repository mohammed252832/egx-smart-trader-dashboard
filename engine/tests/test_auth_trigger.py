from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "supabase/migrations/20261126021608_allow_auth_bootstrap_updates_without_role.sql"
SHARED_ACCOUNT_MIGRATION = ROOT / "supabase/migrations/20261127005539_shared_password_account.sql"
LEGACY_CLEANUP_MIGRATION = ROOT / "supabase/migrations/20261127011012_remove_legacy_dashboard_accounts.sql"
SCHEMA = ROOT / "supabase/schema.sql"
LEGACY_ACCOUNT_EMAILS = (
    "kigobigo11@wm.com",
    "mohammed.fathi2532@wm.com",
    "wael@wm.com",
)


def trigger_function(sql: str) -> str:
    start = sql.index("create or replace function private.enforce_allowed_auth_user()")
    end = sql.index("\n$$;", start) + len("\n$$;")
    return sql[start:end]


class AuthTriggerMigrationTests(unittest.TestCase):
    def test_empty_email_change_is_allowed_but_pending_change_is_rejected(self) -> None:
        for path in (MIGRATION, SCHEMA):
            with self.subTest(path=path.name):
                function = trigger_function(path.read_text(encoding="utf-8"))
                self.assertIn("if nullif(new.email_change, '') is not null then", function)
                self.assertNotIn("if new.email_change is not null then", function)

    def test_bootstrap_and_email_reassignment_guards_remain(self) -> None:
        function = trigger_function(MIGRATION.read_text(encoding="utf-8"))
        self.assertIn("if tg_op = 'UPDATE' and new.email is distinct from old.email then", function)
        self.assertIn("where email = lower(new.email)", function)
        self.assertIn("not in ('', 'member')", function)
        self.assertIn("if tg_op = 'UPDATE'", function)
        self.assertIn("and coalesce(new.raw_app_meta_data ->> 'role', '') <> 'member'", function)
        self.assertIn("and coalesce(old.raw_app_meta_data ->> 'role', '') <> '' then", function)

    def test_fresh_schema_matches_follow_up_migration(self) -> None:
        self.assertEqual(
            trigger_function(SCHEMA.read_text(encoding="utf-8")),
            trigger_function(MIGRATION.read_text(encoding="utf-8")),
        )


class SharedAccountMigrationTests(unittest.TestCase):
    def test_additive_migration_only_enables_shared_account(self) -> None:
        sql = SHARED_ACCOUNT_MIGRATION.read_text(encoding="utf-8")
        self.assertIn("insert into private.allowed_accounts", sql)
        self.assertIn("shared@egx-smart-trader.invalid", sql)
        for email in LEGACY_ACCOUNT_EMAILS:
            self.assertNotIn(email, sql)

    def test_cleanup_migration_requires_ready_shared_account(self) -> None:
        sql = LEGACY_CLEANUP_MIGRATION.read_text(encoding="utf-8")
        self.assertIn("if not exists", sql)
        self.assertIn("shared@egx-smart-trader.invalid", sql)
        self.assertIn("email_confirmed_at is not null", sql)
        self.assertIn("deleted_at is null", sql)
        self.assertIn("banned_until", sql)
        self.assertIn("raw_app_meta_data ->> 'role'", sql)

        delete_sql = sql[sql.index("delete from private.allowed_accounts"):]
        self.assertNotIn("shared@egx-smart-trader.invalid", delete_sql)
        for email in LEGACY_ACCOUNT_EMAILS:
            self.assertIn(email, delete_sql)


if __name__ == "__main__":
    unittest.main()
