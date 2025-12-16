#!/usr/bin/env python3
"""Benchmark FP32 vs INT8 dynamic-quantized ONNX models on CPU.

This script is intended for *local* validation on representative hardware.
It compares:
- model.onnx / model_optimized.onnx (FP32)
- model.quantized.onnx (INT8 dynamic quantization)

Example:
  python benchmarking/onnx_dynamic_quant_benchmark.py --model-dir ./onnx_models

Notes:
- Accuracy validation depends on your dataset. If you provide --data-jsonl with
  {"text": ..., "label": 0/1}, the script reports accuracy and delta.
- If no labeled data is provided, it reports agreement rate between FP32 and INT8.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer


def _pick_fp32_model(model_dir: Path) -> Path:
    for name in ("model_optimized.onnx", "model.onnx"):
        candidate = model_dir / name
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"No FP32 ONNX model found in {model_dir}. Expected model_optimized.onnx or model.onnx"
    )


def _pick_int8_model(model_dir: Path) -> Path:
    for name in ("model.quantized.onnx", "model_quantized.onnx"):
        candidate = model_dir / name
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"No INT8 ONNX model found in {model_dir}. Expected model.quantized.onnx (or legacy model_quantized.onnx)"
    )


def _create_session(model_path: Path, threads: int) -> ort.InferenceSession:
    sess_options = ort.SessionOptions()
    sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    sess_options.intra_op_num_threads = threads
    sess_options.inter_op_num_threads = 1
    return ort.InferenceSession(
        str(model_path),
        sess_options=sess_options,
        providers=["CPUExecutionProvider"],
    )


def _run_batch(
    session: ort.InferenceSession,
    tokenizer: Any,
    texts: list[str],
    max_length: int,
) -> np.ndarray:
    inputs = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=max_length,
        return_tensors="np",
    )
    outputs = session.run(
        None, {"input_ids": inputs["input_ids"], "attention_mask": inputs["attention_mask"]}
    )
    # Expected output: [logits]
    logits = outputs[0]
    return np.asarray(logits)


def _latency_stats(latencies_s: list[float]) -> dict[str, float]:
    lat_sorted = sorted(latencies_s)
    p50 = lat_sorted[int(0.50 * (len(lat_sorted) - 1))]
    p95 = lat_sorted[int(0.95 * (len(lat_sorted) - 1))]
    return {
        "mean_ms": statistics.mean(latencies_s) * 1000,
        "p50_ms": p50 * 1000,
        "p95_ms": p95 * 1000,
    }


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def _default_texts(batch_size: int) -> list[str]:
    texts = [
        "I loved this movie.",
        "This was terrible.",
        "It was okay, not great.",
        "Absolutely fantastic acting.",
        "I would not recommend it.",
        "Pretty good overall.",
        "Boring and too long.",
        "Amazing visuals and story.",
    ]
    return (texts * ((batch_size + len(texts) - 1) // len(texts)))[:batch_size]


def _benchmark_session(
    session: ort.InferenceSession,
    tokenizer: Any,
    texts: list[str],
    *,
    warmup: int,
    runs: int,
    max_length: int,
    batch_size: int,
) -> dict[str, float]:
    for _ in range(warmup):
        _ = _run_batch(session, tokenizer, texts, max_length=max_length)

    latencies: list[float] = []
    for _ in range(runs):
        t0 = perf_counter()
        _ = _run_batch(session, tokenizer, texts, max_length=max_length)
        latencies.append(perf_counter() - t0)

    stats = _latency_stats(latencies)
    stats["throughput_req_s"] = batch_size / (stats["mean_ms"] / 1000)
    return stats


def _print_perf(
    *,
    fp32_path: Path,
    int8_path: Path,
    fp32_stats: dict[str, float],
    int8_stats: dict[str, float],
) -> None:
    print("Models")
    print(f"  FP32: {fp32_path.name}")
    print(f"  INT8: {int8_path.name}")
    print("\nLatency (per batch)")
    print(
        "  FP32 mean: {mean:.2f} ms | p50: {p50:.2f} | p95: {p95:.2f}".format(
            mean=fp32_stats["mean_ms"],
            p50=fp32_stats["p50_ms"],
            p95=fp32_stats["p95_ms"],
        )
    )
    print(
        "  INT8 mean: {mean:.2f} ms | p50: {p50:.2f} | p95: {p95:.2f}".format(
            mean=int8_stats["mean_ms"],
            p50=int8_stats["p50_ms"],
            p95=int8_stats["p95_ms"],
        )
    )
    print("\nThroughput")
    print(f"  FP32: {fp32_stats['throughput_req_s']:.1f} req/s")
    print(f"  INT8: {int8_stats['throughput_req_s']:.1f} req/s")
    print(f"  Speedup: {fp32_stats['mean_ms'] / int8_stats['mean_ms']:.2f}x")


def _print_accuracy_or_agreement(
    *,
    fp32_sess: ort.InferenceSession,
    int8_sess: ort.InferenceSession,
    tokenizer: Any,
    max_length: int,
    batch_texts: list[str],
    data_jsonl: str | None,
) -> None:
    if data_jsonl:
        records = _load_jsonl(Path(data_jsonl))
        texts_eval = [r["text"] for r in records]
        labels = np.asarray([int(r["label"]) for r in records], dtype=np.int64)

        fp32_logits = _run_batch(fp32_sess, tokenizer, texts_eval, max_length=max_length)
        int8_logits = _run_batch(int8_sess, tokenizer, texts_eval, max_length=max_length)

        fp32_pred = np.argmax(fp32_logits, axis=-1)
        int8_pred = np.argmax(int8_logits, axis=-1)

        fp32_acc = float(np.mean(fp32_pred == labels))
        int8_acc = float(np.mean(int8_pred == labels))

        print("\nAccuracy")
        print(f"  FP32 acc: {fp32_acc:.4f}")
        print(f"  INT8 acc: {int8_acc:.4f}")
        print(f"  Delta: {int8_acc - fp32_acc:+.4f}")
        return

    fp32_logits = _run_batch(fp32_sess, tokenizer, batch_texts, max_length=max_length)
    int8_logits = _run_batch(int8_sess, tokenizer, batch_texts, max_length=max_length)
    agreement = float(np.mean(np.argmax(fp32_logits, axis=-1) == np.argmax(int8_logits, axis=-1)))
    print("\nAgreement (no labels provided)")
    print(f"  FP32 vs INT8 predicted-label agreement: {agreement:.3f}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark FP32 vs INT8 dynamic quantized ONNX models (CPU)"
    )
    parser.add_argument(
        "--model-dir", type=str, required=True, help="Directory containing ONNX model + tokenizer"
    )
    parser.add_argument("--warmup", type=int, default=10, help="Warmup iterations per model")
    parser.add_argument("--runs", type=int, default=50, help="Measured iterations per model")
    parser.add_argument("--batch-size", type=int, default=8, help="Batch size")
    parser.add_argument("--max-length", type=int, default=128, help="Tokenizer max_length")
    parser.add_argument("--threads", type=int, default=1, help="ORT intra-op threads")
    parser.add_argument(
        "--data-jsonl",
        type=str,
        default=None,
        help='Optional labeled data JSONL with {"text": str, "label": 0/1} for accuracy comparison',
    )

    args = parser.parse_args()

    model_dir = Path(args.model_dir)
    fp32_path = _pick_fp32_model(model_dir)
    int8_path = _pick_int8_model(model_dir)

    tokenizer = AutoTokenizer.from_pretrained(str(model_dir), use_fast=True)

    fp32_sess = _create_session(fp32_path, threads=args.threads)
    int8_sess = _create_session(int8_path, threads=args.threads)

    texts = _default_texts(args.batch_size)

    fp32_stats = _benchmark_session(
        fp32_sess,
        tokenizer,
        texts,
        warmup=args.warmup,
        runs=args.runs,
        max_length=args.max_length,
        batch_size=args.batch_size,
    )
    int8_stats = _benchmark_session(
        int8_sess,
        tokenizer,
        texts,
        warmup=args.warmup,
        runs=args.runs,
        max_length=args.max_length,
        batch_size=args.batch_size,
    )

    _print_perf(
        fp32_path=fp32_path, int8_path=int8_path, fp32_stats=fp32_stats, int8_stats=int8_stats
    )
    _print_accuracy_or_agreement(
        fp32_sess=fp32_sess,
        int8_sess=int8_sess,
        tokenizer=tokenizer,
        max_length=args.max_length,
        batch_texts=texts,
        data_jsonl=args.data_jsonl,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
