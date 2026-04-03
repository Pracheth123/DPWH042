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
    assert 0.0 <= data["score"] <= 1.0
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
