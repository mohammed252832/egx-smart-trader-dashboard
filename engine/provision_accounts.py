from __future__ import annotations

import argparse
import os
from typing import Any
from urllib.parse import urlparse

import requests

SHARED_ACCOUNT_EMAIL = "shared@egx-smart-trader.invalid"
LEGACY_ACCOUNT_EMAILS = (
    "kigobigo11@wm.com",
    "mohammed.fathi2532@wm.com",
    "wael@wm.com",
)


def _request(
    session: requests.Session,
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    json: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = session.request(
        method,
        url,
        headers=headers,
        json=json,
        params=params,
        timeout=20,
    )
    if not response.ok:
        raise RuntimeError(f"Supabase Admin {method} {url.rsplit('/', 1)[-1]} failed ({response.status_code})")
    if response.status_code == 204 or not response.content:
        return {}
    return response.json()


def _list_users(session: requests.Session, base_url: str, headers: dict[str, str]) -> list[dict[str, Any]]:
    users: list[dict[str, Any]] = []
    page = 1
    while True:
        payload = _request(
            session,
            "GET",
            f"{base_url}/admin/users",
            headers=headers,
            params={"page": page, "per_page": 1000},
        )
        rows = payload.get("users")
        if not isinstance(rows, list):
            raise RuntimeError("Supabase Admin user list did not contain users")
        users.extend(row for row in rows if isinstance(row, dict))
        if len(rows) < 1000:
            return users
        page += 1


def _verify_shared_login(
    session: requests.Session,
    base_url: str,
    secret_key: str,
    shared_password: str,
) -> None:
    payload = _request(
        session,
        "POST",
        f"{base_url}/token",
        headers={"apikey": secret_key, "Content-Type": "application/json"},
        json={"email": SHARED_ACCOUNT_EMAIL, "password": shared_password},
        params={"grant_type": "password"},
    )
    access_token = payload.get("access_token")
    try:
        user = payload.get("user")
        if not isinstance(user, dict):
            raise RuntimeError("Shared dashboard sign-in did not return a user")
        if str(user.get("email") or "").strip().lower() != SHARED_ACCOUNT_EMAIL:
            raise RuntimeError("Shared dashboard sign-in returned an unexpected user")
        metadata = user.get("app_metadata")
        if not isinstance(metadata, dict) or metadata.get("role") != "member":
            raise RuntimeError("Shared dashboard sign-in did not include the member role")
        if not isinstance(access_token, str) or not access_token:
            raise RuntimeError("Shared dashboard sign-in did not return an access token")
    finally:
        if isinstance(access_token, str) and access_token:
            try:
                _request(
                    session,
                    "POST",
                    f"{base_url}/logout",
                    headers={
                        "apikey": secret_key,
                        "Authorization": f"Bearer {access_token}",
                    },
                )
            except RuntimeError:
                pass


def _verify_dashboard_login(
    session: requests.Session,
    dashboard_url: str,
    shared_password: str,
) -> None:
    base_url = dashboard_url.rstrip("/")
    login = session.request(
        "POST",
        f"{base_url}/auth/login",
        data={"password": shared_password},
        allow_redirects=False,
        timeout=20,
    )
    if login.status_code not in (303, 307, 308):
        raise RuntimeError("Deployed dashboard rejected the shared password")
    location = urlparse(login.headers.get("Location", ""))
    if location.path != "/" or location.query:
        raise RuntimeError("Deployed dashboard did not redirect to the dashboard after sign-in")

    response = session.request("GET", f"{base_url}/api/recommendations", timeout=20)
    if response.status_code != 200:
        raise RuntimeError("Deployed dashboard API did not authorize the shared session")
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("Deployed dashboard API returned invalid JSON") from exc
    if not isinstance(payload, dict) or "error" in payload:
        raise RuntimeError("Deployed dashboard API returned an authorization error")

    try:
        session.request("POST", f"{base_url}/auth/logout", allow_redirects=False, timeout=20)
    except requests.RequestException:
        print("Warning: could not sign out the live verification session")


def provision_accounts(
    supabase_url: str,
    secret_key: str,
    shared_password: str | None = None,
    *,
    remove_legacy_accounts: bool = False,
    verify_live_login: bool = False,
    dashboard_url: str | None = None,
) -> tuple[int, int, int]:
    if not supabase_url or not secret_key.startswith("sb_secret_"):
        raise RuntimeError("SUPABASE_URL and a new sb_secret_ key are required")
    if shared_password is None or not 8 <= len(shared_password) <= 72:
        raise RuntimeError("SUPABASE_SHARED_PASSWORD must be between 8 and 72 characters")
    if verify_live_login:
        parsed_url = urlparse(dashboard_url or "")
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            raise RuntimeError("A valid HTTPS DASHBOARD_URL is required for live login verification")

    base_url = f"{supabase_url.rstrip('/')}/auth/v1"
    headers = {
        "apikey": secret_key,
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
    }
    created = 0
    updated = 0
    deleted = 0
    with requests.Session() as session:
        users = _list_users(session, base_url, headers)
        by_email = {
            str(user.get("email") or "").strip().lower(): user
            for user in users
        }
        user = by_email.get(SHARED_ACCOUNT_EMAIL)
        if user is None:
            created_user = _request(
                session,
                "POST",
                f"{base_url}/admin/users",
                headers=headers,
                json={
                    "email": SHARED_ACCOUNT_EMAIL,
                    "password": shared_password,
                    "email_confirm": True,
                    "app_metadata": {"role": "member"},
                },
            )
            metadata = created_user.get("app_metadata")
            metadata = dict(metadata) if isinstance(metadata, dict) else {}
            if metadata.get("role") != "member":
                metadata["role"] = "member"
                _request(
                    session,
                    "PUT",
                    f"{base_url}/admin/users/{created_user['id']}",
                    headers=headers,
                    json={"app_metadata": metadata},
                )
            created += 1
            print("Created confirmed shared dashboard account")
        else:
            metadata = user.get("app_metadata")
            metadata = dict(metadata) if isinstance(metadata, dict) else {}
            metadata["role"] = "member"
            _request(
                session,
                "PUT",
                f"{base_url}/admin/users/{user['id']}",
                headers=headers,
                json={
                    "password": shared_password,
                    "email_confirm": True,
                    "app_metadata": metadata,
                },
            )
            updated += 1
            print("Updated shared dashboard account password and authorization")

        _verify_shared_login(session, base_url, secret_key, shared_password)
        print("Verified shared dashboard password sign-in")
        if verify_live_login:
            _verify_dashboard_login(session, dashboard_url or "", shared_password)
            print("Verified shared dashboard login against the deployed site")

        if remove_legacy_accounts:
            for email in LEGACY_ACCOUNT_EMAILS:
                legacy_user = by_email.get(email)
                if legacy_user is None:
                    continue
                _request(
                    session,
                    "DELETE",
                    f"{base_url}/admin/users/{legacy_user['id']}",
                    headers=headers,
                )
                deleted += 1
                print(f"Deleted legacy dashboard account: {email}")
    return created, updated, deleted


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--remove-legacy", action="store_true")
    parser.add_argument("--verify-live-login", action="store_true")
    args = parser.parse_args()
    try:
        provision_accounts(
            os.getenv("SUPABASE_URL", "").strip(),
            os.getenv("SUPABASE_SECRET_KEY", "").strip(),
            os.getenv("SUPABASE_SHARED_PASSWORD") or None,
            remove_legacy_accounts=args.remove_legacy,
            verify_live_login=args.verify_live_login,
            dashboard_url=os.getenv("DASHBOARD_URL", "").strip() or None,
        )
    except Exception as exc:
        print(f"Shared account configuration failed: {type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
