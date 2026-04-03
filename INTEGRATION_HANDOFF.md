# GhostGrid Data Pipeline: Backend & AI Integration Guide

This document maps out the entire data ingestion layer for the GhostGrid project. It acts as the "source of truth" for the Backend, Database, and AI engineers to understand how the data is fetched, normalized, and exported.

---

## 1. Pipeline Architecture

Our pipeline revolves around extracting chaotic external signals (News, Telegram, Google Trends, Financial APIs, Logistics RSS), cleaning them up, and strictly formatting them into highly-structured data streams.

The architecture flows sequentially in three distinct stages:

### Stage A: Ingestion (Scrapers)
We spin up multiple independent micro-scripts to scrape diverse target platforms.
- **`telegram_scraper.py`**: Reads live group messages (aggressively filtering promotional spam).
- **`news_scraper.py` & `rss_scraper.py`**: Ingests Google News RSS focusing on "shortage", "supply chain", etc.
- **`shipping_scraper.py` & `customs_scraper.py`**: Fetches global logistics constraints.
- **`trends_realtime_scraper.py`**: Hits Google Trends for daily demand signals.
- **`commodity_scraper.py`**: Pulls specific exchange rates/assets.

**How They Work:** Every scraper creates records exclusively using our central `schema.create_record()` engine. They append records line-by-line as **JSONL** inside the `data/` folder.

### Stage B: Unification (`merge_data.py`)
This script sweeps through every single `data/*_data.json` file. 
- It normalizes strings (`text.lower().strip()`).
- It applies **deduplication** logic across sources.
- It fuses everything together into a single, combined **JSON Array** file: `data/combined_data.json`.

### Stage C: ML Validation (`data_validator.py`)
Because the AI needs high-fidelity signals without noise, this layer reads `combined_data.json` and evaluates it against strict Positive and Negative keyword tensors.
- **Outputs To:** `data/cleaned_data.json` (Formatted back to **JSONL**, allowing the AI/Database side to cleanly stream records via generator functions).

---

## 2. Global Execution Flow

To generate a fresh batch of validated data, trigger these steps:

```bash
# 1. Run the target scrapers (can be parallelized/scheduled on cron jobs)
python telegram_scraper.py
python rss_scraper.py
python shipping_scraper.py
# ... etc

# 2. Unify all scraped data sets and strip duplicates
python merge_data.py

# 3. Evaluate signals for ML readiness
python data_validator.py
```

---

## 3. Data Schema Contract (Vital for DB)

All validated objects sitting inside our final dataset (`data/cleaned_data.json`) are guaranteed to possess this strict dictionary contour. Your Database tables and AI prompt wrappers should map perfectly against this representation.

```json
{
  "id": "e0a811ce-1961-42cb-bba3-10e9766d6118",          // UUID string
  "source": "telegram",                                 // ENUM (see below)
  "commodity": "rice",                                  // ENUM (see below)
  "location": "unknown",                                // String ('global', 'india', etc)
  "price": null,                                        // Float or null
  "text": "export ban declared heavily impacting shipping speeds", // String (Raw Signal)
  "timestamp": "2026-04-03T19:48:42.165866",            // ISO-8601 UTC String
  "signal_type": "behavior",                            // ENUM (see below)
  "confidence": 0.6                                     // Float (0.0 to 1.0)
}
```

### Enumeration Restrictions

The Backend MUST enforce or anticipate these enums natively:
* **`source`**: `["telegram", "olx", "news", "shipping", "customs", "trends", "rss", "commodity_api"]`
* **`signal_type`**: `["behavior", "price", "logistics", "news"]`
* **`commodity`**: Freeform currently, but heavily biased towards `["rice", "fuel", "logistics", "crypto", "currency", "unknown"]`

---

## 4. Integration Handoff Checklist

**For The Database Engineer:**
- Set `id` to be your Primary Key (`UUID`).
- Assign `timestamp` as the partitioning or sorting index for chronological timeseries queries.
- Read from `data/cleaned_data.json` utilizing a streaming JSONL parser mapping directly onto your schema.

**For The AI / ML Engineer:**
- Target `data/cleaned_data.json`.
- Feed the `text` attribute into embedding generators or LLM contexts.
- Use `confidence` weights if your model handles confidence multiplication.
- Filter the context vectors naturally using the pre-applied `signal_type` classifications.
