from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from engine.provision_accounts import ALLOWED_ACCOUNT_EMAILS, provision_accounts


def response(payload: dict, status: int = 200) -> Mock:
    result = Mock(ok=status < 400, status_code=status)
    result.json.return_value = payload
    return result


def session_for(users: list[dict], created_user: dict | None = None) -> Mock:
    session = Mock()
    session.request.side_effect = lambda method, url, **kwargs: response(
        {"users": users} if method == "GET" else created_user or {"id": "new-user"}
    )
    session.__enter__ = Mock(return_value=session)
    session.__exit__ = Mock(return_value=False)
    return session


class ProvisionAccountsTests(unittest.TestCase):
    def test_creates_only_missing_accounts_with_server_controlled_role(self) -> None:
        existing = {
            "id": "existing-user",
            "email": ALLOWED_ACCOUNT_EMAILS[0],
            "email_confirmed_at": "2026-11-25T10:00:00Z",
            "app_metadata": {"role": "member", "provider": "email"},
        }
        session = session_for([existing])

        with patch("engine.provision_accounts.requests.Session", return_value=session):
            created, updated = provision_accounts("https://project.supabase.co", "sb_secret_test")

        self.assertEqual((created, updated), (2, 0))
        posts = [call for call in session.request.call_args_list if call.args[0] == "POST"]
        self.assertEqual(len(posts), 2)
        self.assertEqual(
            [call.kwargs["json"]["email"] for call in posts],
            list(ALLOWED_ACCOUNT_EMAILS[1:]),
        )
        for call in posts:
            payload = call.kwargs["json"]
            self.assertTrue(payload["email_confirm"])
            self.assertEqual(payload["app_metadata"], {"role": "member"})
            self.assertGreaterEqual(len(payload["password"]), 32)
        puts = [call for call in session.request.call_args_list if call.args[0] == "PUT"]
        self.assertEqual(len(puts), 2)
        for call in puts:
            self.assertEqual(call.kwargs["json"], {"app_metadata": {"role": "member"}})
            self.assertNotIn("password", call.kwargs["json"])
        self.assertFalse(any(call.args[0] == "DELETE" for call in session.request.call_args_list))

    def test_skips_role_update_when_admin_create_already_returns_member(self) -> None:
        session = session_for(
            [],
            created_user={"id": "new-user", "app_metadata": {"role": "member"}},
        )

        with patch("engine.provision_accounts.requests.Session", return_value=session):
            created, updated = provision_accounts("https://project.supabase.co", "sb_secret_test")

        self.assertEqual((created, updated), (3, 0))
        self.assertFalse(any(call.args[0] == "PUT" for call in session.request.call_args_list))

    def test_updates_role_without_resetting_an_existing_password(self) -> None:
        existing = {
            "id": "existing-user",
            "email": ALLOWED_ACCOUNT_EMAILS[0],
            "email_confirmed_at": None,
            "app_metadata": {"plan": "legacy"},
        }
        session = session_for([existing])

        with patch("engine.provision_accounts.requests.Session", return_value=session):
            created, updated = provision_accounts("https://project.supabase.co", "sb_secret_test")

        self.assertEqual((created, updated), (2, 1))
        put = next(call for call in session.request.call_args_list if call.args[0] == "PUT")
        self.assertEqual(
            put.kwargs["json"],
            {"app_metadata": {"plan": "legacy", "role": "member"}, "email_confirm": True},
        )
        self.assertNotIn("password", put.kwargs["json"])

    def test_sets_shared_password_for_existing_accounts_without_recovery_email(self) -> None:
        users = [
            {
                "id": f"user-{index}",
                "email": email,
                "email_confirmed_at": "2026-11-25T10:00:00Z",
                "app_metadata": {"role": "member"},
            }
            for index, email in enumerate(ALLOWED_ACCOUNT_EMAILS)
        ]
        session = session_for(users)

        with patch("engine.provision_accounts.requests.Session", return_value=session):
            created, updated = provision_accounts(
                "https://project.supabase.co",
                "sb_secret_test",
                shared_password="shared-test-password",
            )

        self.assertEqual((created, updated), (0, 3))
        puts = [call for call in session.request.call_args_list if call.args[0] == "PUT"]
        self.assertEqual(len(puts), 3)
        for call in puts:
            self.assertEqual(call.kwargs["json"], {"password": "shared-test-password"})
            self.assertNotIn("recover", call.args[1])
        self.assertFalse(any(call.args[0] == "POST" for call in session.request.call_args_list))

    def test_uses_shared_password_for_missing_accounts(self) -> None:
        session = session_for(
            [],
            created_user={"id": "new-user", "app_metadata": {"role": "member"}},
        )

        with patch("engine.provision_accounts.requests.Session", return_value=session):
            created, updated = provision_accounts(
                "https://project.supabase.co",
                "sb_secret_test",
                shared_password="shared-test-password",
            )

        self.assertEqual((created, updated), (3, 0))
        posts = [call for call in session.request.call_args_list if call.args[0] == "POST"]
        self.assertEqual(len(posts), 3)
        for call in posts:
            self.assertEqual(call.kwargs["json"]["password"], "shared-test-password")
            self.assertTrue(call.kwargs["json"]["email_confirm"])

    def test_rejects_too_short_shared_password(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "at least 6 characters"):
            provision_accounts(
                "https://project.supabase.co",
                "sb_secret_test",
                shared_password="short",
            )

    def test_rejects_legacy_keys(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "sb_secret_"):
            provision_accounts("https://project.supabase.co", "legacy-jwt")


if __name__ == "__main__":
    unittest.main()
