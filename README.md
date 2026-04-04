# 🌐 GhostGrid — Supply Chain Crisis Detection System

> **DP World Hackathon 2026** | Real-time multilingual NLP + geospatial signal intelligence

GhostGrid is an end-to-end supply chain crisis detection platform that continuously scrapes multilingual data (English, Roman Urdu, Hindi), runs it through a fine-tuned mBERT classifier, and visualises live crisis signals on an interactive world map — all in real time.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        GhostGrid Pipeline                       │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────────┐  │
│  │ Data Scraper │───▶│  NLP Model   │───▶│  FastAPI Backend  │  │
│  │  (10 sources)│    │  (mBERT API) │    │  (Signal Store)   │  │
│  └──────────────┘    └──────────────┘    └────────┬──────────┘  │
│                           Ngrok tunnel             │             │
│                      (public HTTPS URL)    ┌───────▼──────────┐  │
│                                            │  React Dashboard  │  │
│                                            │  (Leaflet MapView)│  │
│                                            └───────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

| Service | Technology | Port |
|---------|-----------|------|
| NLP Inference API | FastAPI + fine-tuned mBERT (PyTorch) | `8001` |
| Ngrok Tunnel | Exposes NLP API to public internet | — |
| Backend API | FastAPI + Supabase (PostgreSQL) | `8000` |
| Frontend Dashboard | React 19 + Vite + Leaflet + Recharts | `5173` |
| Live Data Pipeline | PowerShell loop → 10 scrapers | — |

---

## ✨ Key Features

- 🤖 **Fine-tuned mBERT** — Multilingual BERT classifier (English / Roman Urdu / Hindi) trained on a 4-class crisis taxonomy: `shortage_signal`, `price_hike`, `urgency_sale`, `neutral`
- 🛡️ **3-Gate Flagging Filter** — Confidence gate (≥ 0.65) + Signal-type gate + Z-score anomaly gate to eliminate false positives
- 🌍 **Interactive Leaflet Map** — Real-time geolocated crisis signals with severity-coloured markers on a CartoDB dark tile layer
- 📡 **10 Live Scrapers** — Telegram, news feeds, RSS, OLX marketplace, shipping lanes, commodity prices, customs, Google Trends (realtime + RSS), and more
- ⚡ **Live 60-Second Pipeline** — Automatic scrape → merge → validate → feed cycle, no human intervention required after launch
- 📊 **Full Dashboard** — Command Center, Signals Feed, Alerts, Analytics (Recharts), Sources monitor
- 🔔 **WebSocket Alerts** — Real-time alert broadcast from backend to frontend

---

## 📁 Project Structure

```
DP WORLD HACKATHON/
│
├── nlp_model/                    ← AI Brain
│   ├── src/
│   │   ├── api_server.py         ← FastAPI inference endpoint (POST /v1/predict)
│   │   ├── api_schema.py         ← Pydantic request/response schemas
│   │   ├── train_mbert.py        ← mBERT fine-tuning script
│   │   ├── evaluate.py           ← Model evaluation harness
│   │   └── test_fixes.py         ← Smoke test (10 cases, BUG-1 + BUG-2)
│   └── models/ghostgrid_mbert/   ← Trained weights (not in git)
│
├── backend/                      ← Signal Store & API
│   ├── app/
│   │   ├── api/router.py         ← All FastAPI routes
│   │   ├── services/
│   │   │   ├── nlp_service.py    ← Calls NLP API, handles retries
│   │   │   └── signal_processor.py ← 2nd-line gate filter + WebSocket broadcast
│   │   └── db/supabase_db.py     ← Supabase (PostgreSQL) queries
│   ├── main.py                   ← Uvicorn entry point
│   └── .env                      ← Secrets (not in git)
│
├── data_scrapper/                ← Live Data Scrapers
│   ├── telegram_scraper.py
│   ├── news_scraper.py
│   ├── rss_scraper.py
│   ├── olx_scraper.py
│   ├── shipping_scraper.py
│   ├── commodity_scraper.py
│   ├── customs_scraper.py
│   ├── trends_scraper.py
│   ├── trends_realtime_scraper.py
│   ├── trends_rss_scraper.py
│   ├── merge_data.py             ← Combines all scraper outputs
│   ├── data_validator.py         ← Schema validation
│   ├── live_pipeline.ps1         ← 60-second continuous scrape loop ⭐
│   └── utils/
│       └── feed_to_backend.py    ← POSTs validated data to backend
│
├── frontend/                     ← React Dashboard
│   └── src/
│       ├── components/
│       │   ├── MapView.jsx       ← react-leaflet world map ⭐
│       │   ├── Layout.jsx
│       │   ├── Sidebar.jsx
│       │   ├── MetricCard.jsx
│       │   ├── AlertDrawer.jsx
│       │   ├── ConfidenceGauge.jsx
│       │   ├── SignalBadge.jsx
│       │   └── Toast.jsx
│       ├── pages/
│       │   ├── CommandCenter.jsx ← Main dashboard with Leaflet MapView
│       │   ├── SignalsFeed.jsx
│       │   ├── Alerts.jsx
│       │   ├── Analytics.jsx
│       │   └── Sources.jsx
│       └── context/
│           ├── AlertsContext.jsx
│           ├── SourcesContext.jsx
│           └── UIContext.jsx
│
├── start_ghostgrid.ps1           ← 🚀 ONE-COMMAND LAUNCHER
├── start.ps1                     ← Legacy launcher (without Ngrok)
└── .gitignore
```

---

## 🚀 Running the Project — One Command

Open **any PowerShell window** and run:

```powershell
cd "c:\PRACHETH FILES\DP WORLD HACKATHON"; Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force; .\start_ghostgrid.ps1
```

That's it. The script handles everything automatically.

---

## 📋 What the Launcher Does

The script opens **5 terminal windows** in sequence:

| Window | Service | What it runs |
|--------|---------|-------------|
| **Window 1** | 🧠 NLP Server | `uvicorn src.api_server:app --port 8001` |
| **Window 2** | 🌐 Ngrok Tunnel | `ngrok http 8001` (public HTTPS URL) |
| **Window 3** | ⚙️ Backend API | `uvicorn main:app --reload --port 8000` |
| **Window 4** | 🖥️ Frontend | `npm run dev --port 5173` |
| **Window 5** | 📡 Live Pipeline | `live_pipeline.ps1` (60s scrape loop) |

After opening all windows, the launcher **pauses and asks you to paste the Ngrok URL** from Window 2. It then automatically patches `backend/.env` with the new URL so the backend always knows where to reach the NLP model — even after a Ngrok restart.

```
  ACTION REQUIRED  --  Paste your Ngrok URL below
  Look at Window 2 (Ngrok). Find the line:
    Forwarding   https://xxxx-xx-xxx.ngrok-free.app -> http://localhost:8001
  Paste Ngrok URL here (or press Enter to skip): https://xxxx.ngrok-free.app
```

---

## 🔗 Service URLs (after launch)

| Service | URL |
|---------|-----|
| NLP API health | http://localhost:8001/health |
| NLP API docs | http://localhost:8001/docs |
| Backend health | http://localhost:8000/health |
| **Backend API docs** | **http://localhost:8000/docs** |
| **Frontend Dashboard** | **http://localhost:5173** |

> ⚠️ **Wait ~30 seconds** after launch for the mBERT model to finish loading. Watch Window 1 for `Ready to serve requests on POST /v1/predict`.

---

## ⚙️ Prerequisites

| Requirement | Notes |
|------------|-------|
| Python 3.10+ | With `.venv` at project root |
| Node.js 18+ | For the React frontend |
| ngrok | [Download](https://ngrok.com/download) — must be on PATH |
| CUDA GPU (optional) | RTX 4050+ recommended for fast inference; CPU also works |

### First-time setup

```powershell
# 1. Create virtual environment at project root
python -m venv .venv
.venv\Scripts\pip install -r backend\requirements.txt
.venv\Scripts\pip install -r nlp_model\requirements.txt

# 2. Install frontend dependencies
cd frontend
npm install
cd ..

# 3. Configure backend secrets
# Edit backend\.env and fill in your Supabase URL and key
# (NLP_API_URL will be auto-updated by the launcher each run)
```

---

## 🤖 NLP Model Details

The classifier is a fine-tuned `bert-base-multilingual-cased` model.

### 4-Class Taxonomy

| Class | Description |
|-------|-------------|
| `shortage_signal` | Supply shortage detected |
| `price_hike` | Price spike or inflation signal |
| `urgency_sale` | Panic buying / distress sale |
| `neutral` | No crisis signal |

### 3-Gate Flagging Filter (BUG-2 Fix)

| Gate | Rule |
|------|------|
| **Gate 1 — Confidence** | `< 0.40` → discard; `0.40–0.65` → store only; `≥ 0.65` → alert eligible |
| **Gate 2 — Signal Type** | `shortage_signal` / `price_hike` → alert; `urgency_sale` needs `≥ 0.80`; `neutral` → never flagged |
| **Gate 3 — Z-score** | Anomaly score `> 2.0` required (skipped if baseline < 10 samples) |

### Commodity Extraction (BUG-1 Fix)

12-category keyword dictionary covering: `fuel`, `wheat`, `rice`, `edible_oil`, `sugar`, `fertilizer`, `cotton`, `steel`, `cement`, `medicine`, `electronics`, `shipping` — with word-boundary matching for short keywords (e.g. `\brice\b` to prevent matching inside `"price"`).

---

## 📡 API Reference

### `POST /v1/predict` (NLP API — port 8001)

```json
// Request
{
  "normalized_text": "Wheat prices doubled overnight in Karachi. Major shortage.",
  "commodity": "",
  "source": "telegram"
}

// Response
{
  "signal_type": "shortage_signal",
  "confidence": 0.87,
  "severity": "high",
  "category": "supply",
  "commodity": "wheat",
  "location": "karachi",
  "flagged": true
}
```

### `GET /api/alerts` (Backend — port 8000)

Returns the latest crisis alerts from the Supabase database.

### `WebSocket /ws/alerts` (Backend — port 8000)

Real-time alert stream consumed by the React dashboard.

---

## 🛑 Stopping the System

- Close Windows 1–5 individually, or press `Ctrl+C` in each terminal.
- The launcher window itself can be closed at any time — the 5 service windows keep running independently.

---

## 🔮 Roadmap

- [ ] Replace Ngrok with a static domain (ngrok paid plan or self-hosted tunnel)
- [ ] Connect `MapView` directly to `GET /api/alerts` with its own refresh cycle
- [ ] Increase mBERT training epochs for higher confidence outputs
- [ ] Add commodity-level trend charts to Analytics dashboard
- [ ] Expand location dictionary beyond 24 cities
- [ ] Docker Compose deployment (post-hackathon)

---

## 👥 Team

Built for the **DP World Hackathon 2026** — GhostGrid Team.

---

*GhostGrid — See the signals before the crisis hits.*
