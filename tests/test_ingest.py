"""
tests/test_ingest.py
--------------------
Unit tests for POST /api/ingest.
Uses FastAPI's TestClient (backed by httpx) — no live server needed.
"""

import pytest
from fastapi.testclient import TestClient

from app.api.router import app
from app.db import mock_db as _mock_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_db():
    """Reset MOCK_DB before each test to guarantee isolation."""
    _mock_db.MOCK_DB.clear()
    yield
    _mock_db.MOCK_DB.clear()


def test_ingest_valid_urdu_signal():
    payload = {
        "source_type": "telegram",
        "raw_text": "آٹا نہیں مل رہا، قیمتیں بڑھ گئی ہیں",
        "commodity": "flour",
    }
    response = client.post("/api/ingest", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    assert "created_at" in data
    assert data["source_type"] == "telegram"
    assert data["language"] in ("ur", "ar", "sw", "en", "unknown")
    assert data["signal_type"] in ("shortage_signal", "price_hike", "urgency_sale", "neutral")
    assert 0.0 <= data["confidence"] <= 1.0
    assert data["severity"] in ("low", "medium", "high")


def test_ingest_valid_arabic_signal():
    payload = {
        "source_type": "olx",
        "raw_text": "نقص حاد في الزيت، الأسعار ترتفع بشكل كبير",
        "commodity": "oil",
        "reported_price": 150.0,
    }
    response = client.post("/api/ingest", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["commodity"] == "oil"
    assert data["reported_price"] == 150.0


def test_ingest_valid_swahili_signal():
    payload = {
        "source_type": "forum",
        "raw_text": "Uhaba wa mafuta bei ghali sana sokoni leo",
        "commodity": "fuel",
    }
    response = client.post("/api/ingest", json=payload)
    assert response.status_code == 201


def test_ingest_persists_to_db():
    payload = {
        "source_type": "manual",
        "raw_text": "Cooking oil shortage reported in three districts",
        "commodity": "cooking oil",
    }
    client.post("/api/ingest", json=payload)
    assert len(_mock_db.MOCK_DB) == 1


def test_ingest_rejects_missing_source_type():
    response = client.post("/api/ingest", json={"raw_text": "some text"})
    assert response.status_code == 422


def test_ingest_rejects_text_too_short():
    response = client.post("/api/ingest", json={"source_type": "telegram", "raw_text": "hi"})
    assert response.status_code == 422


def test_ingest_rejects_invalid_source_type():
    response = client.post("/api/ingest", json={"source_type": "twitter", "raw_text": "some longer text here"})
    assert response.status_code == 422


def test_ingest_accepts_new_optional_fields():
    """message_id, notes, and region flow through and appear in the response."""
    payload = {
        "source_type": "telegram",
        "raw_text": "Cooking oil shortage in northern region, prices tripling",
        "commodity": "oil",
        "message_id": "tg_9876543210",
        "notes": "Confirmed by field agent on 2026-04-03",
        "region": "Karachi",
    }
    response = client.post("/api/ingest", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["message_id"] == "tg_9876543210"
    assert data["notes"] == "Confirmed by field agent on 2026-04-03"
    assert data["region"] == "Karachi"


def test_ingest_rejects_notes_too_long():
    """notes has a max_length of 500 characters."""
    payload = {
        "source_type": "manual",
        "raw_text": "Flour shortage in the market, prices rising fast",
        "notes": "x" * 501,
    }
    response = client.post("/api/ingest", json=payload)
    assert response.status_code == 422


def test_ingest_sanitizes_control_characters():
    """Null bytes and control chars are stripped; newlines are preserved."""
    payload = {
        "source_type": "forum",
        "raw_text": "Shortage\x00 reported\x01 in district\nPrices rising fast",
    }
    response = client.post("/api/ingest", json=payload)
    assert response.status_code == 201
    stored = _mock_db.MOCK_DB[0]["raw_text"]
    assert "\x00" not in stored
    assert "\x01" not in stored
    assert "\n" in stored  # newline is preserved


def test_ingest_duplicate_message_id_returns_409():
    """Sending the same message_id twice must return 409 on the second request."""
    payload = {
        "source_type": "telegram",
        "raw_text": "Wheat shortage confirmed, prices up 40 percent in market",
        "message_id": "tg_dedup_001",
    }
    first = client.post("/api/ingest", json=payload)
    assert first.status_code == 201

    second = client.post("/api/ingest", json=payload)
    assert second.status_code == 409
    assert "tg_dedup_001" in second.json()["detail"]


def test_ingest_none_message_id_not_deduplicated():
    """Two records with message_id=None must both succeed (None is not a dedup key)."""
    payload = {
        "source_type": "manual",
        "raw_text": "Cooking oil shortage reported in southern district today",
        "message_id": None,
    }
    r1 = client.post("/api/ingest", json=payload)
    r2 = client.post("/api/ingest", json=payload)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert len(_mock_db.MOCK_DB) == 2
