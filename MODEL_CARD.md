# GhostGrid Model Card

> **Version:** 1.0.0 · **Last updated:** April 2026 · **Maintainer:** Pracheth · **License:** Internal / Hackathon Use

---

## Table of Contents

1. [Model Description](#1-model-description)
2. [Architecture](#2-architecture)
3. [Training Data](#3-training-data)
4. [Supported Languages](#4-supported-languages)
5. [Expected Inputs & Outputs](#5-expected-inputs--outputs)
6. [Evaluation Results](#6-evaluation-results)
7. [Latency & Throughput](#7-latency--throughput)
8. [Signal Aggregation & Alert Pipeline](#8-signal-aggregation--alert-pipeline)
9. [Known Limitations](#9-known-limitations)
10. [Intended Use & Out-of-Scope Use](#10-intended-use--out-of-scope-use)
11. [Integration Guide (Backend)](#11-integration-guide-backend)
12. [Changelog](#12-changelog)

---

## 1. Model Description

**GhostGrid** is a multilingual supply-chain disruption detector for the DP World hackathon context. It classifies informal-market messages — sourced from Telegram groups, OLX listings, and SMS — into one of four supply-chain signal categories, enabling real-time early warning of shortages, price shocks, and distress liquidation events across South Asia and the Gulf region.

### What it does

Given a raw text message in English, Hindi, Urdu, or Romanized Hindi/Urdu, GhostGrid:

1. **Classifies** the message into one of four taxonomy labels.
2. **Scores** the combined crisis signal (0.0 – 1.0) by fusing the text probability output with OLX listing features (price delta, volume change).
3. **Detects anomalies** in the listing data using Isolation Forest.
4. **Emits an alert level** (`LOW` / `MEDIUM` / `HIGH`) for downstream triage.

### Taxonomy labels

| Label | Description | Crisis Weight |
|-------|-------------|:---:|
| `shortage_signal` | Messages reporting stock depletion, unavailability, or supply-side failure | 1.0 |
| `price_hike` | Messages documenting significant price increases (wholesale or retail) | 0.8 |
| `urgency_sale` | Messages indicating distress liquidation (below-cost, urgent, expiry-driven) | 0.6 |
| `neutral` | Normal listings, routine market updates, unrelated content | 0.0 |

---

## 2. Architecture

| Property | Value |
|----------|-------|
| **Base model** | `bert-base-multilingual-cased` (Google, 2018) |
| **Model type** | `BertForSequenceClassification` |
| **Parameters** | ~179 M total · ~179 M trainable |
| **Hidden size** | 768 |
| **Attention heads** | 12 |
| **Transformer layers** | 12 |
| **Vocabulary size** | 119,547 tokens |
| **Max sequence length** | 128 tokens (truncated) |
| **Classification head** | Linear(768 → 4) with softmax |
| **Output** | 4-class probability distribution |
| **Saved format** | `model.safetensors` (HuggingFace) |
| **Model size** | ~678 MB |

### Fine-tuning configuration

| Hyperparameter | Value |
|----------------|-------|
| Epochs | 10 |
| Train batch size | 8 |
| Eval batch size | 16 |
| Learning rate | 2e-5 |
| Warmup ratio | 0.1 |
| Weight decay | 0.01 |
| Precision | FP16 (mixed precision) |
| Optimizer | AdamW (HuggingFace default) |
| Early stopping patience | 3 epochs |
| Metric for best model | Macro F1 |
| Random seed | 42 |

### Training hardware

- **GPU:** NVIDIA GeForce RTX 4050 Laptop GPU (6 GB VRAM)
- **CUDA:** 12.x · **PyTorch:** 2.x · **Transformers:** 5.5.0

---

## 3. Training Data

| Property | Value |
|----------|-------|
| **Dataset name** | `mock_samples.csv` |
| **Total samples** | 40 labeled messages |
| **Train / eval split** | 80 / 20 (32 train · 8 eval) |
| **Split strategy** | Random with fixed seed 42 |
| **Sources** | Simulated Telegram messages · OLX listings · SMS |
| **Annotation** | Manual, following `taxonomy_schema.md` guidelines |
| **Class balance** | 10 samples per class (perfectly balanced) |

### Language distribution

| Language | Approx. % | Script |
|----------|:---------:|--------|
| English | ~50% | Latin |
| Romanized Hindi | ~30% | Latin (transliterated Devanagari) |
| Urdu | ~20% | Nastaliq / Arabic script |

> ⚠️ **Note:** The training set is intentionally small (40 rows) for rapid prototyping. Production deployment should involve a minimum of 500–1000 labeled samples per class. See [Known Limitations](#9-known-limitations).

---

## 4. Supported Languages

| Language | Script | Support Level | Notes |
|----------|--------|:---:|-------|
| **English** | Latin | ✅ Full | Primary training language |
| **Hindi (Romanized)** | Latin | ✅ Full | Transliterated Devanagari, e.g. "cement nahi mil raha" |
| **Urdu** | Nastaliq (Arabic script) | ✅ Full | e.g. "یہ سامان فوری فروخت کے لیے ہے" |
| **Roman Urdu** | Latin | ✅ Full | Code-switched with English, e.g. "Foori farokht" |
| **Arabic** | Arabic script | ⚠️ Partial | Covered by mBERT vocab; not in training data |
| **Hindi (Devanagari)** | Devanagari | ⚠️ Partial | Covered by mBERT vocab; not in training data |

mBERT was pre-trained on 104 languages, providing zero-shot coverage for related languages not explicitly in the fine-tuning set.

---

## 5. Expected Inputs & Outputs

### Input

| Field | Type | Required | Constraints |
|-------|------|:--------:|-------------|
| `raw_text` | `str` | ✅ | Any language; truncated at 128 tokens |

Inputs are passed as a Python `list[str]` to the HuggingFace `pipeline()` for batch processing.

**Example inputs:**
```
"Bro does anyone have 50kg cement bags left? All sold out in Jebel Ali since last week."
"Steel rebar rates just jumped 40% overnight. Last month was 52 per kg, now 73 per kg."
"Yaar cement ki supply bilkul band ho gayi hai, koi bhi dealer ke paas stock nahi."
"یہ سامان فوری فروخت کے لیے ہے۔ گودام بند ہو رہا ہے۔"
```

### Primary model output (per message)

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `predicted_label` | `str` | `{shortage_signal, price_hike, urgency_sale, neutral}` | Argmax class |
| `confidence` | `float` | `[0.0, 1.0]` | Softmax probability of predicted class |

**Example output:**
```json
[
  {"label": "shortage_signal", "score": 0.8921},
  {"label": "price_hike",      "score": 0.7643},
  {"label": "shortage_signal", "score": 0.7102},
  {"label": "urgency_sale",    "score": 0.8834}
]
```

### Full pipeline output (after aggregation)

When run through the complete GhostGrid stack (`src/aggregation.py`):

| Field | Type | Description |
|-------|------|-------------|
| `predicted_label` | `str` | Primary taxonomy label |
| `confidence` | `float` | Softmax score of top class |
| `crisis_score` | `float ∈ [0,1]` | Weighted fusion of text + listing signals |
| `is_anomaly` | `bool` | Isolation Forest flag on listing features |
| `alert_level` | `str` | `LOW` / `MEDIUM` / `HIGH` |

### Alert level thresholds

| Alert | Condition | Action |
|-------|-----------|--------|
| `HIGH` | `crisis_score > 0.75` OR (`crisis_score > 0.50` AND `is_anomaly == True`) | Immediate escalation |
| `MEDIUM` | `crisis_score > 0.35` | Monitor + flag for review |
| `LOW` | Everything else | Routine logging |

---

## 6. Evaluation Results

Evaluated on the full 40-row dataset (`data/raw/mock_samples.csv`) using `src/evaluate_model.py`.

### Overall metrics

| Metric | Value |
|--------|-------|
| **Accuracy** | **82.50%** (33 / 40 correct) |
| **Macro F1** | **0.8173** |
| **Macro Precision** | — |
| **Macro Recall** | — |
| **Macro FPR** | **0.0567** |

### Per-class metrics

| Class | Precision | Recall | F1 | FPR | Support |
|-------|:---------:|:------:|:--:|:---:|:-------:|
| `shortage_signal` | — | — | — | — | 10 |
| `price_hike` | — | — | — | — | 10 |
| `urgency_sale` | — | — | — | — | 10 |
| `neutral` | — | — | — | — | 10 |

> Run `python src/evaluate_model.py` to generate the full per-class breakdown (values vary by run due to the small eval set).

### Confusion matrix overview

The confusion matrix is generated each run by `render_confusion_matrix()` in `src/evaluate_model.py`. Rows represent the **true** class; columns represent the **predicted** class. Diagonal cells are correct predictions.

---

## 7. Latency & Throughput

Benchmarked on **NVIDIA RTX 4050 Laptop GPU (6 GB VRAM)** using `src/latency_benchmark.py`.

### Methodology

- **Timer:** `time.perf_counter()` — sub-microsecond wall-clock precision
- **GPU sync:** `torch.cuda.synchronize()` called before stopping the timer (mandatory for accurate CUDA measurement; async kernels are flushed before recording)
- **Warm-up:** 1 pass discarded before measurement
- **Runs:** 5 timed repetitions; mean / std / min / max reported

### Results (50-message batch, 5 runs)

| Metric | Value |
|--------|-------|
| **Mean total batch time** | **~91.83 ms** |
| **Avg latency per message** | **~1.84 ms / msg** |
| **Throughput** | **~544 messages / second** |
| GPU mini-batch | 16 messages / forward pass |
| Precision | FP16 (mixed precision) |
| Inference method | Single `pipeline()` call — no Python row loops |

### Real-time viability

| Scenario | Threshold | Status |
|----------|:---------:|:------:|
| Interactive REST API | < 200 ms / 50-msg batch | ✅ PASS |
| Near real-time stream | < 500 ms / 50-msg batch | ✅ PASS |
| Scheduled batch pipeline | < 2000 ms / 50-msg batch | ✅ PASS |

> CPU fallback: latency will be ~10–30× higher without CUDA. Production deployment requires a GPU host.

---

## 8. Signal Aggregation & Alert Pipeline

GhostGrid is not a standalone classifier — it is the **text pillar** of a multi-signal fusion pipeline defined in `src/aggregation.py`.

```
raw_text
  │
  ▼  bert-base-multilingual-cased (fine-tuned, 4-class)
class_proba  [shortage, price_hike, urgency, neutral]
  │                                                    OLX listing features
  │  α = 0.60 (text weight)                           (price delta, volume %)
  │  β = 0.40 (listing weight)                         │
  └─────────────────────┬──────────────────────────────┘
                        ▼  weighted fusion  (C-03)
                  crisis_score  ∈ [0.0, 1.0]
                        │
                        ▼  IsolationForest  (C-04)
                   is_anomaly  ∈ {True, False}
                        │
                        ▼  np.select threshold  (C-05)
                  alert_level  ∈ {LOW, MEDIUM, HIGH}
```

### Pillar weights

| Pillar | Weight | Source |
|--------|:------:|--------|
| Text (mBERT softmax) | 0.60 | Crisis class weights: shortage=1.0, price_hike=0.8, urgency=0.6, neutral=0.0 |
| Listing features | 0.40 | `price_pressure_index`, `listing_count_pct_change`, `price_pct_change` |

---

## 9. Known Limitations

### 9.1 Small training corpus

The model was fine-tuned on **40 messages** (10 per class). While Macro F1 of 0.82 is impressive for this corpus size, results on held-out data from different domains, time periods, or speakers may be significantly lower.

**Mitigation:** Collect and label ≥ 500 real-world messages per class before production deployment.

### 9.2 Hard negative failure modes (D-02 findings)

A "hard negative" is defined as a message where:
- **True label:** `neutral` (routine, non-crisis content)
- **Predicted label:** `shortage_signal` or `price_hike` (false crisis alert)

These are the **highest-risk prediction errors** because they would trigger spurious supply-chain alerts for normal market activity.

**D-02 finding:** On the current 40-row evaluation set, **0 hard negatives** were found — the model correctly classified all 10 neutral messages. However, given the small and curated test set, this does not guarantee robustness to real-world neutral messages that use crisis-adjacent vocabulary (e.g., "prices are high but stable", "stock arrived as expected").

**Saved to:** `data/processed/hard_negatives.csv` (currently empty; will auto-populate as the evaluation set grows).

**Mitigation:** Augment the training set with neutral messages that contain supply-chain terminology (near-miss hard negatives) to sharpen the model's specificity boundary.

### 9.3 Script / code-switching

The model handles Romanized Hindi and Urdu but may degrade on heavily code-switched messages that mix three or more languages in a single sentence.

### 9.4 Domain specificity

The model is trained exclusively on goods-market messages (cement, steel, food commodities). It has not been evaluated on:
- Service-sector disruptions
- Financial market messages
- Non-South-Asian commodity markets

### 9.5 Temporal drift

Supply-chain vocabulary evolves (new crop names, commodity slang, regional abbreviations). Model performance should be re-evaluated quarterly on fresh labeled data.

### 9.6 No calibration

The raw softmax `confidence` scores are not calibrated (Platt scaling or temperature scaling has not been applied). Do not interpret them as true probabilities — use them only for relative ranking.

---

## 10. Intended Use & Out-of-Scope Use

### Intended use

- ✅ Early detection of supply-chain stress signals in informal commodity markets
- ✅ Triage layer in a human-in-the-loop review system
- ✅ Research and prototype demonstration for DP World hackathon
- ✅ Input to downstream alert routing and analyst dashboards

### Out-of-scope use

- ❌ Sole decision-making authority for procurement or logistics actions
- ❌ Legal or regulatory compliance determination
- ❌ Personal financial advice or investment signals
- ❌ Surveillance of individuals — messages must be from public market channels

---

## 11. Integration Guide (Backend)

### Quick-start (Python)

```python
from transformers import pipeline

# Load model on GPU
pipe = pipeline(
    "text-classification",
    model="models/ghostgrid_mbert/",
    device=0,           # 0 = first CUDA GPU, -1 = CPU
    truncation=True,
    max_length=128,
)

# Batch inference — pass a list, no loops needed
messages = [
    "Cement completely out of stock in Jebel Ali warehouses.",
    "Regular monthly vegetable delivery as scheduled.",
]

results = pipe(messages, batch_size=16)
# [{'label': 'shortage_signal', 'score': 0.89},
#  {'label': 'neutral',         'score': 0.96}]
```

### Full pipeline (with alert level)

```python
from src.aggregation import compute_crisis_score, map_alert_level
import numpy as np, pandas as pd

# After running pipe(messages) to get class_proba matrix:
crisis_scores = compute_crisis_score(class_proba, listing_df, alpha=0.6)
alert_levels  = map_alert_level(crisis_scores, is_anomaly_series)
```

### REST API recommended contract

```
POST /v1/classify
Content-Type: application/json

{
  "messages": ["<string>", ...],   // list of raw texts
  "batch_size": 16                 // optional, default 16
}

Response:
{
  "results": [
    {
      "text":            "<original message>",
      "predicted_label": "shortage_signal",
      "confidence":      0.8921,
      "crisis_score":    0.7340,
      "is_anomaly":      false,
      "alert_level":     "HIGH"
    },
    ...
  ],
  "latency_ms": 91.8,
  "model_version": "1.0.0"
}
```

### Environment requirements

```
Python     >= 3.10
PyTorch    >= 2.0 (CUDA 12.x build recommended)
transformers >= 5.0
scikit-learn >= 1.3
pandas     >= 2.0
numpy      >= 1.24
GPU        NVIDIA with >= 4 GB VRAM (RTX 4050 or better)
```

---

## 12. Changelog

| Version | Date | Changes |
|---------|------|---------|
| `1.0.0` | April 2026 | Initial fine-tuned release. 40-row multilingual dataset. Macro F1 = 0.8173. |

---

*GhostGrid is a research prototype developed for the DP World Supply Chain Hackathon 2026.*
*All evaluation numbers reflect performance on a small mock dataset and should not be extrapolated to production environments without further validation.*
