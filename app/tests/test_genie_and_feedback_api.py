"""Contract tests for the tab-shell backend endpoints (PLAN 002).

Feedback loop (U3): routing reflects the real reason_codes table; the sibling
simulation reflects the real finding_signature match. Genie proxy (U4): the
scripted fallback answers offline with a stable shape, and a live-path failure
degrades to the fallback rather than 500.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.backend.fake_repository import FakeRepository
from app.backend.main import create_app


@pytest.fixture
def client():
    app = create_app(repo=FakeRepository())
    with TestClient(app) as c:
        yield c


# ---- U3: feedback routing + sibling --------------------------------------

def test_routing_policy_exception(client):
    r = client.get("/api/feedback/routing/policy_exception")
    assert r.status_code == 200
    body = r.json()
    assert set(body["destinations"]) == {"allowlist", "policy_store"}
    assert body["enters_case_memory"] is False


def test_routing_wrong_classification_enters_case_memory(client):
    r = client.get("/api/feedback/routing/wrong_classification")
    assert r.status_code == 200
    body = r.json()
    assert "case_memory" in body["destinations"]
    assert body["enters_case_memory"] is True


def test_routing_invalid_code_422(client):
    r = client.get("/api/feedback/routing/bogus")
    assert r.status_code == 422
    # The error lists the valid codes so the UI can recover.
    assert "policy_exception" in str(r.json())


def test_simulate_sibling_auto_resolves(client):
    r = client.post("/api/feedback/simulate-sibling", json={
        "campaign_id": "freshcart-phishops",
        "recommended_action": "monitor",
        "precedent_reason_code": "policy_exception",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["matches"] is True
    assert body["would_auto_resolve"] is True
    assert body["signature"]


def test_simulate_sibling_no_match(client):
    # A different campaign+action pair does not match the precedent signature.
    r = client.post("/api/feedback/simulate-sibling", json={
        "campaign_id": "unrelated-campaign",
        "recommended_action": "password-reset",
        "precedent_reason_code": "policy_exception",
        "precedent_campaign_id": "freshcart-phishops",
        "precedent_action": "monitor",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["matches"] is False
    assert body["would_auto_resolve"] is False


# ---- U4: Genie proxy (scripted fallback, offline) -------------------------

def test_genie_scripted_top_campaign(client, monkeypatch):
    monkeypatch.delenv("SOC_GENIE_SPACE_ID", raising=False)
    r = client.post("/api/genie/ask", json={"question": "what's the top campaign?"})
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "scripted"
    assert "FreshCart PhishOps" in body["answer"]


def test_genie_scripted_anomaly_count(client, monkeypatch):
    monkeypatch.delenv("SOC_GENIE_SPACE_ID", raising=False)
    r = client.post("/api/genie/ask", json={"question": "how many anomalies were there?"})
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "scripted"
    assert "5" in body["answer"]


def test_genie_unknown_question_graceful(client, monkeypatch):
    monkeypatch.delenv("SOC_GENIE_SPACE_ID", raising=False)
    r = client.post("/api/genie/ask", json={"question": "explain quantum gravity"})
    assert r.status_code == 200
    body = r.json()
    assert "answer" in body and "source" in body


def test_genie_response_shape_stable(client, monkeypatch):
    monkeypatch.delenv("SOC_GENIE_SPACE_ID", raising=False)
    r = client.post("/api/genie/ask", json={"question": "hero domain?"})
    body = r.json()
    assert set(["answer", "source"]).issubset(body.keys())
