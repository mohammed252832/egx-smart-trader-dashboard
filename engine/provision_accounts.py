from __future__ import annotations

import os
import secrets
from typing import Any

import requests

ALLOWED_ACCOUNT_EMAILS = (
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


def provision_accounts(
    supabase_url: str,
    secret_key: str,
    shared_password: str | None = None,
) -> tuple[int, int]:
    if not supabase_url or not secret_key.startswith("sb_secret_"):
        raise RuntimeError("SUPABASE_URL and a new sb_secret_ key are required")
    if shared_password is not None and len(shared_password) < 6:
        raise RuntimeError("The shared password must be at least 6 characters")

    base_url = f"{supabase_url.rstrip('/')}/auth/v1"
    headers = {
        "apikey": secret_key,
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
    }
    created = 0
    updated = 0
    with requests.Session() as session:
        users = _list_users(session, base_url, headers)
        by_email = {
            str(user.get("email") or "").strip().lower(): user
            for user in users
        }
        for email in ALLOWED_ACCOUNT_EMAILS:
            user = by_email.get(email)
            if user is None:
                created_user = _request(
                    session,
                    "POST",
                    f"{base_url}/admin/users",
                    headers=headers,
                    json={
                        "email": email,
                        "password": shared_password or secrets.token_urlsafe(32),
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
                print(f"Created confirmed dashboard account: {email}")
                continue

            metadata = user.get("app_metadata")
            metadata = dict(metadata) if isinstance(metadata, dict) else {}
            payload: dict[str, Any] = {}
            if metadata.get("role") != "member":
                metadata["role"] = "member"
                payload["app_metadata"] = metadata
            if not user.get("email_confirmed_at"):
                payload["email_confirm"] = True
            if shared_password is not None:
                payload["password"] = shared_password
            if payload:
                _request(
                    session,
                    "PUT",
                    f"{base_url}/admin/users/{user['id']}",
                    headers=headers,
                    json=payload,
                )
                updated += 1
                action = "authorization and password" if "password" in payload else "authorization"
                print(f"Updated dashboard account {action}: {email}")
            else:
                print(f"Dashboard account already ready: {email}")
    return created, updated


def main() -> int:
    try:
        provision_accounts(
            os.getenv("SUPABASE_URL", "").strip(),
            os.getenv("SUPABASE_SECRET_KEY", "").strip(),
            os.getenv("SUPABASE_SHARED_PASSWORD") or None,
        )
    except Exception as exc:
        print(f"Account provisioning failed: {type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
