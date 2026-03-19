"""Basic tests for webhook endpoint (Epic 1 done-criteria)."""

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.config.settings import settings

client = TestClient(app)

_SECRET = "test_secret"


def _make_signature(body: bytes, secret: str = _SECRET) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


@pytest.fixture(autouse=True)
def patch_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "onebox_webhook_secret", _SECRET)


class TestWebhookOneBox:
    def _payload(self) -> dict:
        return {"event_type": "deal_created", "deal_id": 42}

    def test_valid_signature_returns_200(self) -> None:
        body = json.dumps(self._payload()).encode()
        resp = client.post(
            "/api/v1/webhook/onebox",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-OneBox-Signature": _make_signature(body),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "accepted"
        assert "event_id" in data

    def test_invalid_signature_returns_401(self) -> None:
        body = json.dumps(self._payload()).encode()
        resp = client.post(
            "/api/v1/webhook/onebox",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-OneBox-Signature": "sha256=deadbeef",
            },
        )
        assert resp.status_code == 401

    def test_missing_signature_returns_401(self) -> None:
        body = json.dumps(self._payload()).encode()
        resp = client.post(
            "/api/v1/webhook/onebox",
            content=body,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 401

    def test_unknown_source_no_hmac_check(self) -> None:
        """Non-onebox sources skip HMAC (other auth strategies in their adapters)."""
        body = json.dumps({"event_type": "ping"}).encode()
        resp = client.post(
            "/api/v1/webhook/external",
            content=body,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200


class TestHealth:
    def test_health_returns_200(self) -> None:
        # Redis may not be available in unit test env — that's fine,
        # we only verify the endpoint itself responds.
        resp = client.get("/health")
        assert resp.status_code == 200
        assert "status" in resp.json()
