from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "supabase/migrations/20261126010647_fix_auth_user_empty_email_change.sql"
SCHEMA = ROOT / "supabase/schema.sql"


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

    def test_signup_and_email_reassignment_guards_remain(self) -> None:
        function = trigger_function(MIGRATION.read_text(encoding="utf-8"))
        self.assertIn("if tg_op = 'UPDATE' and new.email is distinct from old.email then", function)
        self.assertIn("where email = lower(new.email)", function)
        self.assertIn("coalesce(new.raw_app_meta_data ->> 'role', '') <> 'member'", function)

    def test_fresh_schema_matches_follow_up_migration(self) -> None:
        self.assertEqual(
            trigger_function(SCHEMA.read_text(encoding="utf-8")),
            trigger_function(MIGRATION.read_text(encoding="utf-8")),
        )


if __name__ == "__main__":
    unittest.main()
