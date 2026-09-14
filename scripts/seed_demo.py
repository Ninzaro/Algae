"""Seed synthetic bars into a running paper runtime via the API (operator token required)."""

from __future__ import annotations

import os

import httpx


def main() -> None:
    base = os.environ.get("ALPHAFORGE_API", "http://localhost:8000")
    email = os.environ.get("OPERATOR_EMAIL", "operator@localhost")
    password = os.environ.get("OPERATOR_PASSWORD", "change-me")
    with httpx.Client(timeout=30.0) as client:
        token = client.post(
            f"{base}/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        token.raise_for_status()
        access = token.json()["access_token"]
        headers = {"Authorization": f"Bearer {access}"}
        cycle = client.post(f"{base}/api/v1/strategies/cycle", headers=headers)
        cycle.raise_for_status()
        print("cycle", cycle.json())


if __name__ == "__main__":
    main()
