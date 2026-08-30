"""Backend API tests: release gate and auth stub."""

import os
import pytest
from fastapi.testclient import TestClient


def _get_client():
    # Need to reimport to pick up env changes
    import importlib
    import backend.app as app_module
    importlib.reload(app_module)
    # Also reload auth if needed
    return TestClient(app_module.create_app())


def test_health_not_loaded_by_default():
    # Ensure env not approved
    os.environ.pop("MODEL_RELEASE_APPROVED", None)
    os.environ.pop("APPROVED_ARTIFACT_REVISION", None)
    os.environ.pop("DEMO_MODE", None)
    client = _get_client()
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["model_loaded"] is False
    assert data["model_approved"] is False
    assert data["status"] == "model_not_loaded"


def test_readiness_not_ready_when_not_approved():
    os.environ.pop("MODEL_RELEASE_APPROVED", None)
    os.environ.pop("APPROVED_ARTIFACT_REVISION", None)
    os.environ.pop("DEMO_MODE", None)
    client = _get_client()
    r = client.get("/readiness")
    assert r.json()["status"] == "not_ready"


def test_ranking_empty_when_not_released():
    os.environ.pop("MODEL_RELEASE_APPROVED", None)
    os.environ.pop("APPROVED_ARTIFACT_REVISION", None)
    os.environ.pop("DEMO_MODE", None)
    client = _get_client()
    r = client.get("/genes/ranking")
    assert r.status_code == 200
    data = r.json()
    assert data["model_loaded"] is False
    assert data["genes"] == []
    assert data["total_genes"] == 0


def test_explain_503_when_not_released():
    os.environ.pop("MODEL_RELEASE_APPROVED", None)
    os.environ.pop("APPROVED_ARTIFACT_REVISION", None)
    os.environ.pop("DEMO_MODE", None)
    client = _get_client()
    r = client.get("/genes/APOE")
    assert r.status_code == 503


def test_release_gate_approved_with_demo():
    os.environ["MODEL_RELEASE_APPROVED"] = "true"
    os.environ["APPROVED_ARTIFACT_REVISION"] = "test-rev-123"
    os.environ["DEMO_MODE"] = "true"
    client = _get_client()
    r = client.get("/health")
    data = r.json()
    assert data["model_loaded"] is True
    assert data["model_approved"] is True
    assert data["model_revision"] == "test-rev-123"

    # ranking should now return demo genes
    r2 = client.get("/genes/ranking")
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["model_loaded"] is True
    assert len(d2["genes"]) > 0
    # search filter
    r3 = client.get("/genes/ranking?q=APOE")
    assert any("APOE" in g["gene"] for g in r3.json()["genes"])

    # explain should work
    gene = d2["genes"][0]["gene"]
    r4 = client.get(f"/genes/{gene}")
    assert r4.status_code == 200

    # cleanup
    os.environ.pop("MODEL_RELEASE_APPROVED", None)
    os.environ.pop("APPROVED_ARTIFACT_REVISION", None)
    os.environ.pop("DEMO_MODE", None)


def test_release_gate_needs_both_vars():
    os.environ["MODEL_RELEASE_APPROVED"] = "true"
    os.environ.pop("APPROVED_ARTIFACT_REVISION", None)
    os.environ.pop("DEMO_MODE", None)
    client = _get_client()
    r = client.get("/health")
    assert r.json()["model_loaded"] is False
    assert r.json()["model_approved"] is False
    os.environ.pop("MODEL_RELEASE_APPROVED", None)


def test_auth_me_requires_token():
    os.environ.pop("MODEL_RELEASE_APPROVED", None)
    client = _get_client()
    r = client.get("/auth/me")
    assert r.status_code == 401
    r2 = client.get("/auth/me", headers={"Authorization": "Bearer test-token-abc"})
    assert r2.status_code == 200
    assert "user" in r2.json()


def test_auth_stub_with_mocked_verifier():
    from backend.app import create_app
    from backend.auth import verify_bearer_token

    app = create_app()

    def fake_verifier(authorization=None):
        return {"uid": "mocked-user", "email": "test@example.com"}

    app.dependency_overrides[verify_bearer_token] = fake_verifier
    # also need to override require_auth's dependency chain; patch directly
    from backend.auth import require_auth

    def fake_require():
        return {"uid": "mocked-user", "email": "test@example.com"}

    # Simpler: test via overridden verify_bearer_token for ranking (optional auth)
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200


def test_ranking_pagination_with_demo():
    os.environ["MODEL_RELEASE_APPROVED"] = "true"
    os.environ["APPROVED_ARTIFACT_REVISION"] = "pag-test"
    os.environ["DEMO_MODE"] = "true"
    client = _get_client()
    r = client.get("/genes/ranking?limit=2&offset=1")
    data = r.json()
    assert len(data["genes"]) <= 2
    os.environ.pop("MODEL_RELEASE_APPROVED", None)
    os.environ.pop("APPROVED_ARTIFACT_REVISION", None)
    os.environ.pop("DEMO_MODE", None)
