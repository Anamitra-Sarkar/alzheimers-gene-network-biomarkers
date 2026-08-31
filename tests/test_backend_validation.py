"""Validation/error-path tests for backend API (no 500 on malformed input)."""

import os
import pytest
from fastapi.testclient import TestClient


def _client_demo():
    os.environ["MODEL_RELEASE_APPROVED"] = "true"
    os.environ["APPROVED_ARTIFACT_REVISION"] = "test-validation-rev"
    os.environ["DEMO_MODE"] = "true"
    import importlib
    import backend.app as app_module
    importlib.reload(app_module)
    return TestClient(app_module.create_app())


def _client_unreleased():
    os.environ.pop("MODEL_RELEASE_APPROVED", None)
    os.environ.pop("APPROVED_ARTIFACT_REVISION", None)
    os.environ.pop("DEMO_MODE", None)
    import importlib
    import backend.app as app_module
    importlib.reload(app_module)
    return TestClient(app_module.create_app())


def test_ranking_invalid_limit_returns_422():
    client = _client_demo()
    r = client.get("/genes/ranking?limit=0")
    assert r.status_code == 422
    r2 = client.get("/genes/ranking?limit=201")
    assert r2.status_code == 422
    r3 = client.get("/genes/ranking?limit=abc")
    assert r3.status_code == 422


def test_ranking_invalid_offset_returns_422():
    client = _client_demo()
    r = client.get("/genes/ranking?offset=-1")
    assert r.status_code == 422


def test_ranking_offset_beyond_total_returns_empty_not_error():
    client = _client_demo()
    r = client.get("/genes/ranking?limit=10&offset=1000")
    assert r.status_code == 200
    data = r.json()
    assert data["genes"] == []
    assert data["total_genes"] >= 0


def test_ranking_q_too_long_returns_422():
    client = _client_demo()
    long_q = "A" * 101
    r = client.get(f"/genes/ranking?q={long_q}")
    assert r.status_code == 422


def test_ranking_empty_q_treated_as_none():
    client = _client_demo()
    r = client.get("/genes/ranking?q=%20%20")
    assert r.status_code == 200


def test_explain_not_found_returns_404():
    client = _client_demo()
    r = client.get("/genes/FAKEGENE9999")
    assert r.status_code == 404


def test_explain_invalid_chars_returns_422():
    client = _client_demo()
    # gene_id pattern ^[A-Za-z0-9._\-]+$  -- slash or space should be rejected
    r = client.get("/genes/BAD!@#")
    assert r.status_code == 422


def test_explain_too_long_returns_422():
    client = _client_demo()
    long_id = "A" * 65
    r = client.get(f"/genes/{long_id}")
    assert r.status_code == 422


def test_explain_503_when_not_released_returns_clean_json():
    client = _client_unreleased()
    r = client.get("/genes/APOE")
    assert r.status_code == 503
    assert "detail" in r.json()


def test_health_always_200_even_when_unreleased():
    client = _client_unreleased()
    r = client.get("/health")
    assert r.status_code == 200
    assert "model_loaded" in r.json()
    assert "model_approved" in r.json()


def test_ranking_unreleased_always_200_with_empty():
    client = _client_unreleased()
    r = client.get("/genes/ranking?limit=5&offset=0&q=APOE")
    assert r.status_code == 200
    assert r.json()["genes"] == []
    assert r.json()["model_loaded"] is False


def test_auth_me_returns_401_without_token():
    client = _client_unreleased()
    r = client.get("/auth/me")
    assert r.status_code == 401
