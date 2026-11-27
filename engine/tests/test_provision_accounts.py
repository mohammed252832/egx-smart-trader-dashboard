from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import requests

from engine.provision_accounts import (
    LEGACY_ACCOUNT_EMAILS,
    SHARED_ACCOUNT_EMAIL,
    provision_accounts,
)


def response(payload: dict, status: int = 200) -> Mock:
    result = Mock(ok=status < 400, status_code=status, content=b"{}")
    result.json.return_value = payload
    return result


def session_for(users: list[dict], created_user: dict | None = None) -> Mock:
    session = Mock()

    def request(method: str, url: str, **kwargs: object) -> Mock:
        if method == "GET" and url.endswith("/admin/users"):
            return response({"users": users})
        if method == "POST" and url.endswith("/token"):
            return response(
                {
                    "access_token": "test-access-token",
                    "user": {
                        "email": SHARED_ACCOUNT_EMAIL,
                        "app_metadata": {"role": "member"},
                    },
                }
            )
        if method == "POST" and url.endswith("/logout"):
            return response({}, status=204)
        if method == "DELETE":
            return response({}, status=204)
        return response(created_user or {"id": "new-user"})

    session.request.side_effect = request
    session.__enter__ = Mock(return_value=session)
    session.__exit__ = Mock(return_value=False)
    return session


class ProvisionAccountsTests(unittest.TestCase):
    def test_creates_shared_account_with_server_controlled_role(self) -> None:
        session = session_for(
            [],
            created_user={"id": "new-user", "app_metadata": {"role": "member"}},
        )

        with patch("engine.provision_accounts.requests.Session", return_value=session):
            created, updated, deleted = provision_accounts(
                "https://project.supabase.co",
                "sb_secret_test",
                shared_password="shared-test-password",
            )

        self.assertEqual((created, updated, deleted), (1, 0, 0))
        post = next(call for call in session.request.call_args_list if call.args[0] == "POST")
        self.assertEqual(
            post.kwargs["json"],
            {
                "email": SHARED_ACCOUNT_EMAIL,
                "password": "shared-test-password",
                "email_confirm": True,
                "app_metadata": {"role": "member"},
            },
        )
        self.assertFalse(any(call.args[0] == "DELETE" for call in session.request.call_args_list))

    def test_updates_existing_shared_account_password_and_role(self) -> None:
        existing = {
            "id": "shared-user",
            "email": SHARED_ACCOUNT_EMAIL,
            "email_confirmed_at": None,
            "app_metadata": {"plan": "legacy"},
        }
        session = session_for([existing])

        with patch("engine.provision_accounts.requests.Session", return_value=session):
            created, updated, deleted = provision_accounts(
                "https://project.supabase.co",
                "sb_secret_test",
                shared_password="shared-test-password",
            )

        self.assertEqual((created, updated, deleted), (0, 1, 0))
        put = next(call for call in session.request.call_args_list if call.args[0] == "PUT")
        self.assertEqual(
            put.kwargs["json"],
            {
                "password": "shared-test-password",
                "email_confirm": True,
                "app_metadata": {"plan": "legacy", "role": "member"},
            },
        )

    def test_deletes_legacy_accounts_only_after_shared_account_is_ready(self) -> None:
        users = [
            {
                "id": f"legacy-{index}",
                "email": email,
                "email_confirmed_at": "2026-11-25T10:00:00Z",
                "app_metadata": {"role": "member"},
            }
            for index, email in enumerate(LEGACY_ACCOUNT_EMAILS)
        ]
        session = session_for(users)

        with patch("engine.provision_accounts.requests.Session", return_value=session):
            created, updated, deleted = provision_accounts(
                "https://project.supabase.co",
                "sb_secret_test",
                shared_password="shared-test-password",
                remove_legacy_accounts=True,
            )

        self.assertEqual((created, updated, deleted), (1, 0, 3))
        methods = [call.args[0] for call in session.request.call_args_list]
        self.assertLess(methods.index("POST"), methods.index("DELETE"))
        deletes = [call for call in session.request.call_args_list if call.args[0] == "DELETE"]
        self.assertEqual(
            [call.args[1].rsplit("/", 1)[-1] for call in deletes],
            ["legacy-0", "legacy-1", "legacy-2"],
        )

    def test_does_not_delete_legacy_accounts_if_shared_sign_in_fails(self) -> None:
        users = [{"id": "legacy-user", "email": LEGACY_ACCOUNT_EMAILS[0], "app_metadata": {"role": "member"}}]
        session = session_for(users)
        default_request = session.request.side_effect

        def request(method: str, url: str, **kwargs: object) -> Mock:
            if method == "POST" and url.endswith("/token"):
                return response({}, status=401)
            return default_request(method, url, **kwargs)

        session.request.side_effect = request

        with patch("engine.provision_accounts.requests.Session", return_value=session):
            with self.assertRaisesRegex(RuntimeError, "sign-in|token"):
                provision_accounts(
                    "https://project.supabase.co",
                    "sb_secret_test",
                    shared_password="shared-test-password",
                    remove_legacy_accounts=True,
                )

        self.assertFalse(any(call.args[0] == "DELETE" for call in session.request.call_args_list))

    def test_verifies_deployed_login_before_deleting_legacy_accounts(self) -> None:
        users = [{"id": "legacy-user", "email": LEGACY_ACCOUNT_EMAILS[0], "app_metadata": {"role": "member"}}]
        session = session_for(users)
        default_request = session.request.side_effect

        def request(method: str, url: str, **kwargs: object) -> Mock:
            if url == "https://dashboard.example/auth/login":
                result = response({}, status=303)
                result.headers = {"Location": "/"}
                return result
            if url == "https://dashboard.example/api/recommendations":
                return response({"recommendations": []})
            if url == "https://dashboard.example/auth/logout":
                return response({}, status=303)
            return default_request(method, url, **kwargs)

        session.request.side_effect = request

        with patch("engine.provision_accounts.requests.Session", return_value=session):
            provision_accounts(
                "https://project.supabase.co",
                "sb_secret_test",
                shared_password="shared-test-password",
                remove_legacy_accounts=True,
                verify_live_login=True,
                dashboard_url="https://dashboard.example",
            )

        urls = [call.args[1] for call in session.request.call_args_list]
        self.assertLess(urls.index("https://dashboard.example/auth/login"), urls.index("https://dashboard.example/auth/logout"))
        delete_index = next(index for index, call in enumerate(session.request.call_args_list) if call.args[0] == "DELETE")
        self.assertLess(urls.index("https://dashboard.example/api/recommendations"), delete_index)

    def test_does_not_delete_legacy_accounts_if_deployed_login_fails(self) -> None:
        users = [{"id": "legacy-user", "email": LEGACY_ACCOUNT_EMAILS[0], "app_metadata": {"role": "member"}}]
        session = session_for(users)
        default_request = session.request.side_effect

        def request(method: str, url: str, **kwargs: object) -> Mock:
            if url == "https://dashboard.example/auth/login":
                result = response({}, status=303)
                result.headers = {"Location": "/login?error=invalid"}
                return result
            return default_request(method, url, **kwargs)

        session.request.side_effect = request

        with patch("engine.provision_accounts.requests.Session", return_value=session):
            with self.assertRaisesRegex(RuntimeError, "redirect to the dashboard"):
                provision_accounts(
                    "https://project.supabase.co",
                    "sb_secret_test",
                    shared_password="shared-test-password",
                    remove_legacy_accounts=True,
                    verify_live_login=True,
                    dashboard_url="https://dashboard.example",
                )

        self.assertFalse(any(call.args[0] == "DELETE" for call in session.request.call_args_list))

    def test_keeps_legacy_accounts_by_default(self) -> None:
        users = [
            {"id": "legacy-user", "email": LEGACY_ACCOUNT_EMAILS[0], "app_metadata": {"role": "member"}}
        ]
        session = session_for(users)

        with patch("engine.provision_accounts.requests.Session", return_value=session):
            provision_accounts(
                "https://project.supabase.co",
                "sb_secret_test",
                shared_password="shared-test-password",
            )

        self.assertFalse(any(call.args[0] == "DELETE" for call in session.request.call_args_list))

    def test_does_not_delete_legacy_accounts_if_shared_account_creation_fails(self) -> None:
        session = session_for(
            [{"id": "legacy-user", "email": LEGACY_ACCOUNT_EMAILS[0], "app_metadata": {"role": "member"}}]
        )

        def request(method: str, url: str, **kwargs: object) -> Mock:
            if method == "GET":
                return response({"users": [{"id": "legacy-user", "email": LEGACY_ACCOUNT_EMAILS[0]}]})
            if method == "POST":
                raise requests.RequestException("creation failed")
            return response({}, status=204)

        session.request.side_effect = request

        with patch("engine.provision_accounts.requests.Session", return_value=session):
            with self.assertRaises(requests.RequestException):
                provision_accounts(
                    "https://project.supabase.co",
                    "sb_secret_test",
                    shared_password="shared-test-password",
                    remove_legacy_accounts=True,
                )

        self.assertFalse(any(call.args[0] == "DELETE" for call in session.request.call_args_list))

    def test_requires_shared_password_of_supported_length(self) -> None:
        for password in (None, "short", "x" * 73):
            with self.subTest(password=password):
                with self.assertRaisesRegex(RuntimeError, "between 8 and 72"):
                    provision_accounts(
                        "https://project.supabase.co",
                        "sb_secret_test",
                        shared_password=password,
                    )

    def test_rejects_legacy_keys(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "sb_secret_"):
            provision_accounts(
                "https://project.supabase.co",
                "legacy-jwt",
                shared_password="shared-test-password",
            )


if __name__ == "__main__":
    unittest.main()
