"""
tests/test_alerts.py
--------------------
Unit tests for GET /api/alerts and GET /api/alerts/{id}.
Seeds MOCK_DB directly for full control over test data.
"""

import pytest
from fastapi.testclient import TestClient

from app.api.router import app
from app.db import mock_db as _mock_db

client = TestClient(app)

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_db():
    _mock_db.MOCK_DB.clear()
    yield
    _mock_db.MOCK_DB.clear()


def _seed(signal_type: str, confidence: float, language: str = "en", severity: str = "medium") -> dict:
    """Helper: insert a pre-built record directly into MOCK_DB."""
    return _mock_db.insert_signal({
        "source_type": "telegram",
        "raw_text": "Test signal text for unit testing purposes.",
        "source_url": None,
        "reported_price": None,
        "commodity": "wheat",
        "message_id": None,
        "notes": None,
        "region": None,
        "language": language,
        "signal_type": signal_type,
        "confidence": confidence,
        "severity": severity,
    })


# ── List alerts ───────────────────────────────────────────────────────────────

def test_alerts_empty_when_db_empty():
    response = client.get("/api/alerts")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["alerts"] == []


def test_alerts_excludes_neutral_signals():
    _seed("neutral", 0.5)
    response = client.get("/api/alerts")
    assert response.json()["total"] == 0


def test_alerts_returns_non_neutral_signals():
    _seed("shortage_signal", 0.8, severity="high")
    _seed("price_hike", 0.6, severity="medium")
    response = client.get("/api/alerts")
    data = response.json()
    assert data["total"] == 2


def test_alerts_sorted_by_confidence_descending():
    _seed("shortage_signal", 0.9, severity="high")
    _seed("price_hike", 0.4, severity="medium")
    _seed("urgency_sale", 0.7, severity="high")
    data = client.get("/api/alerts").json()
    scores = [a["confidence"] for a in data["alerts"]]
    assert scores == sorted(scores, reverse=True)


def test_alerts_filter_by_signal_type():
    _seed("shortage_signal", 0.8, severity="high")
    _seed("price_hike", 0.6, severity="medium")
    response = client.get("/api/alerts?signal_type=shortage_signal")
    data = response.json()
    assert all(a["signal_type"] == "shortage_signal" for a in data["alerts"])


def test_alerts_filter_by_severity():
    _seed("shortage_signal", 0.9, severity="high")
    _seed("price_hike", 0.3, severity="low")
    response = client.get("/api/alerts?severity=high")
    data = response.json()
    assert all(a["severity"] == "high" for a in data["alerts"])


def test_alerts_filter_by_language():
    _seed("shortage_signal", 0.8, language="ur", severity="high")
    _seed("price_hike", 0.7, language="ar", severity="high")
    response = client.get("/api/alerts?language=ur")
    data = response.json()
    assert all(a["language"] == "ur" for a in data["alerts"])


# ── Single alert ──────────────────────────────────────────────────────────────

def test_get_alert_by_id_found():
    record = _seed("shortage_signal", 0.8, severity="high")
    response = client.get(f"/api/alerts/{record['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == record["id"]


def test_get_alert_by_id_not_found():
    response = client.get("/api/alerts/nonexistent-uuid")
    assert response.status_code == 404
