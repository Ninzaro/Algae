from fastapi.testclient import TestClient

from alphaforge.api.app import create_app
from alphaforge.core.config import Settings


def test_health_and_login_cycle(settings: Settings) -> None:
    app = create_app(settings)
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        denied = client.get("/api/v1/dashboard")
        assert denied.status_code == 401

        login = client.post(
            "/api/v1/auth/login",
            json={
                "email": settings.operator_email,
                "password": settings.operator_password.get_secret_value(),
            },
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        dash = client.get("/api/v1/dashboard", headers={"Authorization": f"Bearer {token}"})
        assert dash.status_code == 200
        body = dash.json()
        assert body["mode"] == "paper"
        assert "account" in body

        # Test CORS preflight with LAN IP
        preflight = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://192.168.1.71:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert preflight.status_code == 200
        assert preflight.headers.get("access-control-allow-origin") == "http://192.168.1.71:3000"

