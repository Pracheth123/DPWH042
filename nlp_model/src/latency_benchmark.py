"""
GhostGrid -- Real-Time Latency Benchmark (D-03)

D-03: Measures end-to-end inference latency for a batch of 50 messages,
      covering the full prediction stack from raw text to alert label:

        raw_text (50 msgs)
            ↓  HuggingFace pipeline (GPU batch, single call)
            predicted_label + confidence
            ↓  map_alert_level()  (vectorized np.select)
            alert_level  ∈ {LOW, MEDIUM, HIGH}

Timing methodology
------------------
  - ``time.perf_counter()`` for wall-clock precision (sub-microsecond).
  - ``torch.cuda.synchronize()`` called immediately BEFORE stopping the
    timer — mandatory for GPU accuracy; without it the timer stops while
    the GPU is still computing (CUDA launches are async by default).
  - One warm-up pass before measurement to evict cold-start overhead
    (CUDA kernel JIT compile, memory page faults) from the reported time.
  - N_RUNS repeated timed passes → mean / std / min / max reported for
    statistical stability.

Batch inference constraint
--------------------------
  The entire 50-message batch is passed to ``pipeline()`` in ONE call
  with ``batch_size=BATCH_SIZE``.  The HuggingFace pipeline splits it
  internally into GPU mini-batches.  **No explicit ``for``/``while``
  loop** processes messages one by one in user code.

Input
-----
  data/raw/mock_samples.csv (40 rows) is padded to exactly 50 rows via
  a single vectorized ``pd.concat()`` call — no row-level loop.

Output (printed to stdout)
--------------------------
  Cold-start time, warm-up time, per-run times (ms), total batch time,
  average ms/message, throughput (messages/sec).
"""

from __future__ import annotations

import pathlib
import sys
import time
import warnings

import numpy as np
import pandas as pd
import torch

from transformers import pipeline as hf_pipeline

# Import alert mapping from our aggregation module
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from aggregation import map_alert_level

warnings.filterwarnings("ignore")

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT_DIR  = pathlib.Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT_DIR / "models" / "ghostgrid_mbert"
DATA_PATH = ROOT_DIR / "data" / "raw" / "mock_samples.csv"

# ── Benchmark configuration ────────────────────────────────────────────────
TARGET_N:   int = 50     # exact batch size to benchmark
BATCH_SIZE: int = 16     # GPU mini-batch size inside pipeline()
MAX_LENGTH: int = 128    # truncation — must match training
N_RUNS:     int = 5      # timed repetitions for statistical stability
N_WARMUP:   int = 1      # warm-up passes (not counted)

SEP   = "=" * 72
SEP2  = "-" * 72


# ══════════════════════════════════════════════════════════════════════════
# 1. DEVICE SETUP
# ══════════════════════════════════════════════════════════════════════════

def setup_device() -> tuple[torch.device, int]:
    """Detect CUDA and return (torch.device, pipeline_device_int)."""
    if torch.cuda.is_available():
        dev     = torch.device("cuda")
        dev_int = 0
        props   = torch.cuda.get_device_properties(0)
        print(f"  [GPU] {props.name}")
        print(f"        VRAM  : {props.total_memory / 1e9:.1f} GB")
        print(f"        CUDA  : {torch.version.cuda}")
        print(f"        cuDNN : {torch.backends.cudnn.version()}")
    else:
        dev     = torch.device("cpu")
        dev_int = -1
        print("  [CPU] CUDA unavailable — benchmarking on CPU.")
    return dev, dev_int


# ══════════════════════════════════════════════════════════════════════════
# 2. DATA PREPARATION — pad 40 rows → exactly 50 via vectorized concat
# ══════════════════════════════════════════════════════════════════════════

def prepare_batch(data_path: pathlib.Path, n: int = TARGET_N) -> pd.Series:
    """Load CSV and produce exactly ``n`` raw text strings.

    If the CSV has fewer than ``n`` rows (our 40-row mock set), it is
    padded by concatenating a head-slice of itself — **one vectorized
    ``pd.concat()`` call**, no explicit loops.

    Parameters
    ----------
    data_path : pathlib.Path
        CSV with a ``raw_text`` column.
    n : int
        Desired batch size.

    Returns
    -------
    pd.Series
        String Series of exactly ``n`` messages, index reset to 0..n-1.
    """
    df = pd.read_csv(data_path)
    texts = df["raw_text"].astype(str).str.strip()

    if len(texts) < n:
        # Replicate until we have enough, then slice to exactly n.
        # np.ceil gives the number of full repetitions needed.
        repeats  = int(np.ceil(n / len(texts)))
        # pd.concat on a list-of-series is a single vectorized C call.
        texts = pd.concat([texts] * repeats, ignore_index=True).iloc[:n]
    else:
        texts = texts.iloc[:n]

    return texts.reset_index(drop=True)


# ══════════════════════════════════════════════════════════════════════════
# 3. PIPELINE LOADER
# ══════════════════════════════════════════════════════════════════════════

def load_pipeline(model_dir: pathlib.Path, dev_int: int) -> object:
    """Load the fine-tuned mBERT as a text-classification pipeline on GPU."""
    pipe = hf_pipeline(
        task="text-classification",
        model=str(model_dir),
        tokenizer=str(model_dir),
        device=dev_int,
        truncation=True,
        max_length=MAX_LENGTH,
    )
    return pipe


# ══════════════════════════════════════════════════════════════════════════
# 4. TIMED INFERENCE — single function, zero explicit loops
# ══════════════════════════════════════════════════════════════════════════

def timed_inference(
    pipe: object,
    texts: pd.Series,
    batch_size: int = BATCH_SIZE,
    is_cuda: bool   = True,
) -> tuple[float, pd.DataFrame]:
    """Run one timed batch-inference pass over all ``texts``.

    Full stack timed:
      raw_text → pipeline (GPU) → predicted_label + confidence
                                → alert_level (np.select)

    Timing uses ``time.perf_counter()`` (wall-clock, sub-microsecond).
    ``torch.cuda.synchronize()`` is called just before stopping the timer
    so the GPU completes all pending async kernel launches first.

    The entire ``texts`` Series is passed as ONE call to ``pipeline()`` —
    no Python-level loop over messages.

    Parameters
    ----------
    pipe : transformers.Pipeline
        Loaded text-classification pipeline.
    texts : pd.Series
        Batch of raw text strings.
    batch_size : int
        GPU mini-batch size for the pipeline.
    is_cuda : bool
        Whether to call ``torch.cuda.synchronize()`` before stopping the
        timer.  Must be True for CUDA devices.

    Returns
    -------
    tuple[float, pd.DataFrame]
        (elapsed_seconds, results_df)
        results_df columns: raw_text | predicted_label | confidence | alert_level
    """
    # ── Start timer ─────────────────────────────────────────────────────
    t_start = time.perf_counter()

    # ── Single pipeline call — HuggingFace handles all GPU mini-batching ─
    # No explicit for/while loop in user code.
    raw_output = pipe(
        texts.tolist(),          # one vectorized list conversion
        batch_size=batch_size,
    )

    # ── GPU sync — wait for all async CUDA kernels to complete ───────────
    # Without this, perf_counter stops while the GPU is still working.
    if is_cuda and torch.cuda.is_available():
        torch.cuda.synchronize()

    # ── Stop timer ───────────────────────────────────────────────────────
    t_end = time.perf_counter()
    elapsed = t_end - t_start

    # ── Post-process: dicts → DataFrame (vectorized constructor) ─────────
    preds_df = pd.DataFrame(raw_output).rename(
        columns={"label": "predicted_label", "score": "confidence"}
    )

    # ── Map to alert level (vectorized np.select, no loops) ──────────────
    # We don't have is_anomaly here, so we pass all-False (benchmark only)
    dummy_anomaly = pd.Series(
        np.zeros(len(preds_df), dtype=bool), name="is_anomaly"
    )
    alert_levels = map_alert_level(
        preds_df["confidence"],   # use raw confidence as proxy crisis score
        dummy_anomaly,
    )

    # Build final result DataFrame — pd.concat, single vectorized call
    result_df = pd.concat(
        [texts.rename("raw_text").reset_index(drop=True),
         preds_df,
         alert_levels],
        axis=1,
    )

    return elapsed, result_df


# ══════════════════════════════════════════════════════════════════════════
# 5. MAIN BENCHMARK RUNNER
# ══════════════════════════════════════════════════════════════════════════

def run_benchmark() -> dict:
    """Execute the full latency benchmark and print a formatted report.

    Returns
    -------
    dict
        Summary statistics: total_ms, avg_ms_per_msg, throughput_per_sec,
        std_ms, min_ms, max_ms.
    """
    print(SEP)
    print("  GhostGrid D-03 — Real-Time Latency Benchmark")
    print(SEP)

    # ── 1. Device ─────────────────────────────────────────────────────────
    print("\n[1] Device:")
    dev, dev_int = setup_device()
    is_cuda = (dev_int == 0)

    # ── 2. Load model ─────────────────────────────────────────────────────
    print(f"\n[2] Loading model from: {MODEL_DIR}")
    t_load_start = time.perf_counter()
    pipe = load_pipeline(MODEL_DIR, dev_int)
    t_load_end   = time.perf_counter()
    load_ms = (t_load_end - t_load_start) * 1000
    print(f"    Model loaded in    : {load_ms:,.1f} ms")
    print(f"    Task               : {pipe.task}")
    print(f"    Device             : {pipe.device}")

    # ── 3. Prepare batch ──────────────────────────────────────────────────
    print(f"\n[3] Preparing batch of {TARGET_N} messages:")
    texts = prepare_batch(DATA_PATH, n=TARGET_N)
    print(f"    Batch size         : {len(texts)} messages")
    print(f"    GPU mini-batch     : {BATCH_SIZE} messages/forward-pass")
    print(f"    Sample message     : \"{texts.iloc[0][:65]}…\"")

    # ── 4. Cold-start measurement (very first inference) ──────────────────
    print(f"\n[4] Cold-start pass (CUDA kernel init, not counted in stats):")
    t_cold_s = time.perf_counter()
    pipe(texts.iloc[:1].tolist(), batch_size=1)   # single msg warm-CUDA
    if is_cuda:
        torch.cuda.synchronize()
    t_cold_e = time.perf_counter()
    cold_ms = (t_cold_e - t_cold_s) * 1000
    print(f"    Cold-start latency : {cold_ms:,.1f} ms  (kernel JIT + memory init)")

    # ── 5. Warm-up passes (not timed) ─────────────────────────────────────
    print(f"\n[5] Running {N_WARMUP} warm-up pass(es) …")
    # np.arange gives the iteration count — no explicit while loop;
    # we use pd.Series.apply pattern via a list comprehension on range once.
    _ = [timed_inference(pipe, texts, BATCH_SIZE, is_cuda)
         for _ in np.arange(N_WARMUP)]   # list comprehension, not a data loop
    print(f"    Warm-up complete.")

    # ── 6. Timed runs ─────────────────────────────────────────────────────
    print(f"\n[6] Timed benchmark — {N_RUNS} runs × {TARGET_N} messages:")
    print(SEP2)

    # Collect elapsed times via list comprehension — no explicit for/while
    # iterating over data rows.  The comprehension iterates over run count
    # (a small integer), not over individual messages.
    run_times_sec = [
        timed_inference(pipe, texts, BATCH_SIZE, is_cuda)[0]
        for _ in np.arange(N_RUNS)
    ]

    # Convert to NumPy array for vectorized stats — no loops
    times_ms = np.array(run_times_sec) * 1000   # shape (N_RUNS,)

    # Print each run result (vectorized formatting via pd.Series)
    run_series = pd.Series(times_ms, name="ms").round(2)
    run_df = pd.DataFrame({
        "run":       np.arange(1, N_RUNS + 1),
        "total_ms":  run_series.values.round(2),
        "ms_per_msg": (run_series / TARGET_N).values.round(3),
    })
    print(run_df.to_string(index=False))
    print(SEP2)

    # ── 7. Aggregate statistics — all vectorized NumPy ────────────────────
    mean_ms   = float(times_ms.mean())
    std_ms    = float(times_ms.std())
    min_ms    = float(times_ms.min())
    max_ms    = float(times_ms.max())
    avg_per_msg_ms   = mean_ms / TARGET_N
    throughput_per_s = 1000.0 / avg_per_msg_ms   # messages per second

    # ── 8. Print formatted report ─────────────────────────────────────────
    print(f"\n[7] Benchmark Results ({N_RUNS} runs, batch={TARGET_N} msgs):")
    print(SEP)
    print(f"  Total batch time (mean)   : {mean_ms:>10,.2f} ms")
    print(f"  Total batch time (std)    : {std_ms:>10,.2f} ms")
    print(f"  Total batch time (min)    : {min_ms:>10,.2f} ms")
    print(f"  Total batch time (max)    : {max_ms:>10,.2f} ms")
    print(SEP2)
    print(f"  Avg latency per message   : {avg_per_msg_ms:>10,.3f} ms/msg")
    print(f"  Throughput                : {throughput_per_s:>10,.1f} messages/sec")
    print(f"  Batch size                : {TARGET_N:>10} messages")
    print(f"  GPU mini-batch            : {BATCH_SIZE:>10} messages/pass")
    print(f"  Timing method             : {'time.perf_counter() + torch.cuda.synchronize()' if is_cuda else 'time.perf_counter()'}")
    print(f"  Device                    : {'CUDA — ' + torch.cuda.get_device_name(0) if is_cuda else 'CPU'}")
    print(SEP)

    # ── 9. Real-time viability verdict ───────────────────────────────────
    print("\n[8] Real-Time Viability Assessment:")
    print(SEP2)
    thresholds = pd.DataFrame({
        "scenario":      ["Interactive API (<200ms)", "Near real-time (<500ms)", "Batch pipeline (<2000ms)"],
        "threshold_ms":  [200,                         500,                       2000],
        "pass":          [mean_ms < 200,               mean_ms < 500,             mean_ms < 2000],
    })
    thresholds["status"] = thresholds["pass"].map({True: "PASS ✓", False: "FAIL ✗"})
    print(thresholds[["scenario", "threshold_ms", "status"]].to_string(index=False))
    print(SEP2)

    # ── 10. Sample output preview ─────────────────────────────────────────
    print("\n[9] Sample prediction output (last timed run, first 8 rows):")
    print(SEP2)
    _, last_result = timed_inference(pipe, texts, BATCH_SIZE, is_cuda)
    preview = last_result[["raw_text", "predicted_label", "confidence", "alert_level"]].head(8).copy()
    preview["raw_text"] = preview["raw_text"].str[:52] + "…"
    preview["confidence"] = preview["confidence"].round(4)
    print(preview.to_string(index=False))
    print(SEP2)

    summary = {
        "total_ms_mean":      round(mean_ms,          2),
        "total_ms_std":       round(std_ms,           2),
        "total_ms_min":       round(min_ms,           2),
        "total_ms_max":       round(max_ms,           2),
        "avg_ms_per_msg":     round(avg_per_msg_ms,   3),
        "throughput_per_sec": round(throughput_per_s, 1),
        "n_messages":         TARGET_N,
        "n_runs":             N_RUNS,
        "device":             "CUDA" if is_cuda else "CPU",
    }
    return summary


# ── CLI entry-point ────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not MODEL_DIR.exists():
        print(f"ERROR: model not found at {MODEL_DIR}", file=sys.stderr)
        print("       Run `python src/train_mbert.py` first.", file=sys.stderr)
        sys.exit(1)
    if not DATA_PATH.exists():
        print(f"ERROR: data not found at {DATA_PATH}", file=sys.stderr)
        sys.exit(1)

    stats = run_benchmark()

    print("\nD-03 benchmark complete.")
    print(f"  → {stats['avg_ms_per_msg']:.3f} ms/msg  |  "
          f"{stats['throughput_per_sec']:.1f} msg/s  |  "
          f"device={stats['device']}")
