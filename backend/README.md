<div align="center">

# 👻 GhostGrid

**Early Warning System for Supply Chain Crises**

*Detects stress signals 3–5 days before they appear in mainstream media*

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## 📖 Overview

GhostGrid monitors **informal markets** — Telegram chats, OLX listings, and local-language forums — to detect early-stage supply chain stress signals that precede mainstream coverage by 3 to 5 days.

It ingests raw, unstructured text in **Urdu, Arabic, Swahili, and English**, runs it through an NLP classification pipeline, and surfaces actionable alerts ranked by severity. The backend is built with **FastAPI** and uses an in-memory store (`MOCK_DB`) that is architected to be swapped out for **Supabase** with a single import change.

### Detected Signal Types

| Signal | Description |
|--------|-------------|
| `shortage_signal` | Scarcity mentions ("can't find flour", "stock ran out") |
| `price_hike` | Informal price surge reports ("price doubled overnight") |
| `urgency_sale` | Desperate sell-offs ("selling diesel cheap, urgent") |
| `neutral` | No stress detected — excluded from alert feeds |

---

## 🗂️ Folder Structure

```
ghostgrid-backend/
│
├── .env                          # Active runtime config (not committed)
├── .env.example                  # Committed template with placeholder values
├── requirements.txt              # Pinned dependencies
├── main.py                       # Entry point — imports and re-exports the app
│
├── app/
│   ├── core/
│   │   ├── config.py             # Pydantic Settings — loads .env
│   │   └── constants.py          # Enums: SignalType, SourceType, SupportedLanguage, SeverityLevel
│   │
│   ├── db/
│   │   └── mock_db.py            # MOCK_DB global list + CRUD helpers (swap here for Supabase)
│   │
│   ├── models/
│   │   ├── signal.py             # SignalIngest (request) + SignalRecord (stored/returned)
│   │   └── alert.py              # AlertResponse + AlertListResponse (API envelopes)
│   │
│   ├── services/
│   │   ├── nlp_service.py        # Language detection + classification stubs (NLP team replaces)
│   │   ├── signal_processor.py   # Orchestrates NLP → scoring → DB insert
│   │   └── alert_service.py      # Alert filtering, ranking, envelope wrapping
│   │
│   ├── api/
│   │   ├── health.py             # GET /health
│   │   ├── ingest.py             # POST /api/ingest
│   │   ├── alerts.py             # GET /api/alerts, GET /api/alerts/{id}
│   │   ├── sources.py            # GET /api/sources
│   │   └── router.py             # FastAPI app instance + middleware mount
│   │
│   └── middleware/
│       └── request_logger.py     # Logs method, path, status, latency per request
│
├── data/
│   ├── raw/                      # Raw scraped dumps — git-ignored
│   └── processed/                # NLP-processed artifacts — git-ignored
│
├── notebooks/                    # Exploratory Jupyter notebooks (NLP team)
│
└── tests/
    ├── test_ingest.py            # 7 tests — POST /api/ingest
    ├── test_alerts.py            # 10 tests — GET /api/alerts + /api/alerts/{id}
    └── test_nlp_service.py       # 14 tests — language detection, classification, severity
```

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` before running the server:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `GhostGrid` | Application name (shown in API docs) |
| `DEBUG` | `false` | Enable verbose debug mode |
| `ALERT_LOOKBACK_HOURS` | `72` | Default time window for alert queries (hours) |
| `MAX_ALERTS_RETURNED` | `50` | Default cap on alerts per response |
| `NLP_MODEL_ENDPOINT` | *(empty)* | Remote NLP inference endpoint (fill when model is ready) |
| `NLP_API_KEY` | *(empty)* | API key for the NLP model service |
| `SUPABASE_URL` | *(empty)* | Supabase project URL (fill when migrating off MOCK_DB) |
| `SUPABASE_KEY` | *(empty)* | Supabase service role key |

> **Note:** The server runs with all variables empty. Only `NLP_MODEL_ENDPOINT` and `SUPABASE_*` need values once the NLP team integrates the real model and the DB is migrated.

---

## 🚀 Installation & Setup

### Prerequisites

- Python 3.10 or higher
- `py` launcher (Windows) or `python3` (Linux/macOS)

### 1. Clone the repository

```bash
git clone https://github.com/your-org/ghostgrid-backend.git
cd ghostgrid-backend
```

### 2. Create a virtual environment (recommended)

```bash
# Windows
py -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
py -m pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env if you need to change defaults — no secrets required for development
```

---

## 🖥️ Running the Server

```bash
py -m uvicorn main:app --reload
```

> **Why `py -m uvicorn`?**  
> On Windows, `uvicorn` may not be added to `PATH` automatically. Using `py -m uvicorn` invokes it through the Python module interface and always works regardless of PATH configuration.

The server starts at:

| URL | Description |
|-----|-------------|
| `http://127.0.0.1:8000` | API root |
| `http://127.0.0.1:8000/docs` | Swagger UI (interactive API explorer) |
| `http://127.0.0.1:8000/redoc` | ReDoc documentation |
| `http://127.0.0.1:8000/health` | Liveness probe |

---

## 📡 API Endpoints

### `GET /health`
Liveness probe. Returns 200 as long as the process is alive.

```bash
curl http://127.0.0.1:8000/health
```

```json
{
  "status": "ok",
  "service": "GhostGrid",
  "timestamp": "2026-04-03T11:00:00+00:00"
}
```

---

### `POST /api/ingest`
Ingest a raw signal from any informal market source.

```bash
# Urdu signal (Telegram)
curl -X POST http://127.0.0.1:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "telegram",
    "raw_text": "آٹا نہیں مل رہا، قیمتیں بڑھ گئی ہیں",
    "commodity": "flour"
  }'

# Arabic signal (OLX listing)
curl -X POST http://127.0.0.1:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "olx",
    "raw_text": "نقص حاد في الزيت، الأسعار ترتفع بشكل كبير",
    "commodity": "oil",
    "reported_price": 150
  }'

# Swahili signal (Forum)
curl -X POST http://127.0.0.1:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "forum",
    "raw_text": "Uhaba wa mafuta bei ghali sana sokoni leo",
    "commodity": "fuel"
  }'
```

**Request body fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source_type` | `string` | ✅ | One of: `telegram`, `olx`, `forum`, `manual` |
| `raw_text` | `string` | ✅ | Raw scraped text (5–5000 characters) |
| `source_url` | `string` | ❌ | Direct link to the original post |
| `reported_price` | `number` | ❌ | Explicit price mentioned in the post |
| `commodity` | `string` | ❌ | Commodity referenced (e.g. `"wheat"`, `"diesel"`) |

**Response (201 Created):**

```json
{
  "id": "a3f2c1d4-...",
  "source_type": "telegram",
  "raw_text": "آٹا نہیں مل رہا، قیمتیں بڑھ گئی ہیں",
  "commodity": "flour",
  "source_url": null,
  "reported_price": null,
  "language": "ur",
  "signal_type": "shortage_signal",
  "score": 0.8421,
  "severity": "high",
  "created_at": "2026-04-03T11:02:29.081084+00:00"
}
```

---

### `GET /api/alerts`
Fetch ranked, non-neutral alerts with optional filters.

```bash
# All alerts in the last 72 hours (default)
curl http://127.0.0.1:8000/api/alerts

# Filter: only high-severity shortage signals in Urdu
curl "http://127.0.0.1:8000/api/alerts?signal_type=shortage_signal&severity=high&language=ur"

# Wider window, higher limit
curl "http://127.0.0.1:8000/api/alerts?lookback_hours=168&limit=100"
```

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lookback_hours` | `int` | `72` | Return alerts from within this many hours (max 720) |
| `limit` | `int` | `50` | Maximum alerts to return (max 200) |
| `signal_type` | `string` | — | Filter: `shortage_signal`, `price_hike`, `urgency_sale` |
| `severity` | `string` | — | Filter: `low`, `medium`, `high` |
| `language` | `string` | — | Filter: `ur`, `ar`, `sw`, `en`, `unknown` |

**Response:**

```json
{
  "total": 2,
  "lookback_hours": 72,
  "generated_at": "2026-04-03T11:05:00+00:00",
  "alerts": [
    {
      "id": "a3f2c1d4-...",
      "source_type": "telegram",
      "language": "ur",
      "signal_type": "shortage_signal",
      "score": 0.8421,
      "severity": "high",
      "commodity": "flour",
      "created_at": "2026-04-03T11:02:29+00:00"
    }
  ]
}
```

---

### `GET /api/alerts/{signal_id}`
Retrieve a single signal by its UUID.

```bash
curl http://127.0.0.1:8000/api/alerts/a3f2c1d4-...
```

Returns the full `SignalRecord` or `404` if not found.

---

### `GET /api/sources`
Source channel health summary — useful for verifying that scrapers are active.

```bash
curl http://127.0.0.1:8000/api/sources
```

```json
[
  {
    "source_type": "telegram",
    "total_signals": 12,
    "last_seen": "2026-04-03T11:02:29+00:00"
  },
  {
    "source_type": "olx",
    "total_signals": 4,
    "last_seen": "2026-04-03T10:55:00+00:00"
  }
]
```

---

## 🧪 Running Tests

```bash
py -m pytest tests/ -v
```

Expected output:

```
tests/test_ingest.py::test_ingest_valid_urdu_signal         PASSED
tests/test_ingest.py::test_ingest_valid_arabic_signal       PASSED
tests/test_ingest.py::test_ingest_valid_swahili_signal      PASSED
tests/test_ingest.py::test_ingest_persists_to_db            PASSED
tests/test_ingest.py::test_ingest_rejects_missing_source    PASSED
tests/test_ingest.py::test_ingest_rejects_text_too_short    PASSED
tests/test_ingest.py::test_ingest_rejects_invalid_source    PASSED

tests/test_alerts.py::test_alerts_empty_when_db_empty       PASSED
tests/test_alerts.py::test_alerts_excludes_neutral_signals  PASSED
...

31 passed in 1.35s
```

Each test file isolates itself using an `autouse` fixture that clears `MOCK_DB` before and after every test — no test state leaks between runs.

---

## 🤖 NLP Team Integration Guide

The classification pipeline in `app/services/nlp_service.py` has two stub functions marked for replacement:

### `detect_language(text: str) -> SupportedLanguage`

Current implementation uses a Unicode block heuristic. Replace the function body with a proper language detection model (e.g. `langdetect`, `fastText`, or HuggingFace `langid`).

```python
# NLP TEAM: REPLACE WITH MULTILINGUAL LANGUAGE DETECTION MODEL
def detect_language(text: str) -> SupportedLanguage:
    ...
```

### `classify_signal(text: str, language: SupportedLanguage) -> tuple[SignalType, float]`

Current implementation returns a random category and score. Replace with your fine-tuned multilingual model (e.g. `mBERT`, `XLM-R`).

```python
# NLP TEAM: INTEGRATE MULTILINGUAL LLM/GPU MODEL HERE
def classify_signal(text, language) -> tuple[SignalType, float]:
    ...
```

**Contract (must not change):**
- Return type: `(SignalType, float)` where `float` is in `[0.0, 1.0]`
- Add `NLP_MODEL_ENDPOINT` and `NLP_API_KEY` to `.env` for remote inference

---

## 🗄️ Supabase Migration Guide

The entire DB layer is isolated in `app/db/mock_db.py`. To migrate:

1. Create `app/db/supabase_db.py` implementing these same function signatures:
   - `insert_signal(record: dict) -> dict`
   - `get_signal_by_id(signal_id: str) -> dict | None`
   - `get_signals_by_source(source_type) -> list[dict]`
   - `get_alerts(lookback_hours, limit) -> list[dict]`
   - `get_source_summary() -> list[dict]`

2. In `app/db/__init__.py`, swap the import:
   ```python
   # from app.db.mock_db import ...
   from app.db.supabase_db import ...
   ```

3. Set `SUPABASE_URL` and `SUPABASE_KEY` in `.env`

No changes needed in services, API routes, or models.

**Target Supabase table schema (`signals`):**

| Column | Type | Notes |
|--------|------|-------|
| `id` | `uuid` | Primary key, default `gen_random_uuid()` |
| `source_type` | `text` | Enum-constrained |
| `raw_text` | `text` | |
| `source_url` | `text` | Nullable |
| `reported_price` | `numeric` | Nullable |
| `commodity` | `text` | Nullable |
| `language` | `text` | |
| `signal_type` | `text` | |
| `score` | `numeric` | |
| `severity` | `text` | |
| `created_at` | `timestamptz` | Default: `now()` |

---

## 🛠️ Tech Stack

| Technology | Purpose |
|-----------|---------|
| **Python 3.10+** | Core runtime |
| **FastAPI** | REST API framework |
| **Uvicorn** | ASGI server |
| **Pydantic v2** | Request/response validation and serialisation |
| **pydantic-settings** | `.env` configuration loading |
| **python-dotenv** | Environment variable support |
| **pytest + httpx** | Testing (no live server required) |

---

## 📋 Severity Score Reference

| Score Range | Severity | Meaning |
|-------------|----------|---------|
| `0.10 – 0.39` | 🟡 `low` | Weak signal, monitor only |
| `0.40 – 0.69` | 🟠 `medium` | Notable stress, track closely |
| `0.70 – 1.00` | 🔴 `high` | Strong crisis indicator, act now |

---

<div align="center">

Built for **DP World** · GhostGrid v0.1.0

</div>
