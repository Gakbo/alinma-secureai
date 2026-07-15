"""
Automatic model benchmarking (upgrade requirement #8).

Trains every candidate listed under benchmark.candidates in the config,
measures quality + cost metrics for each, writes a markdown comparison
report, and recommends the best model.

Run (GPU strongly recommended -- Colab free tier works):
    python sms_model/benchmark_models.py

Metrics per model:
  accuracy, precision, recall, f1, roc_auc   (quality)
  training time, peak GPU memory, model size, inference latency (cost)

Recommendation rule: highest F1; ties broken by roc_auc, then by
inference latency (faster wins). F1 leads because phishing detection cares
about both catching scams (recall) and not crying wolf (precision).
"""
import os
import shutil
import time

import torch

from config_loader import load_config, resolve_model
from train_transformer import train


def _dir_size_mb(path: str) -> float:
    """
    Size of the SAVED MODEL only.

    Skips the 'checkpoints' subfolder -- that holds per-epoch training
    snapshots (2 kept via save_total_limit), which are training artifacts,
    not part of the deployable model. Including them previously reported
    ~7.4GB for a ~1.1GB model.
    """
    total = 0
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d != "checkpoints"]
        for f in files:
            total += os.path.getsize(os.path.join(root, f))
    return total / (1024 * 1024)


def _measure_inference_latency(model_dir: str, n_runs: int = 30) -> float:
    """Average single-message inference latency in milliseconds."""
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)
    model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    sample = "عزيزي العميل، حسابك سيتم إيقافه. Click here to verify now."
    inputs = tokenizer(sample, return_tensors="pt", truncation=True,
                       max_length=128).to(device)
    with torch.no_grad():
        for _ in range(3):                      # warmup
            model(**inputs)
        start = time.perf_counter()
        for _ in range(n_runs):
            model(**inputs)
    return (time.perf_counter() - start) / n_runs * 1000


def run_benchmark():
    cfg = load_config()
    bench = cfg.get("benchmark", {})
    candidates = bench.get("candidates", [])
    epochs = bench.get("epochs", 2)
    report_path = bench.get("report_path", "saved_models/model_benchmark_report.md")

    results = []
    for key in candidates:
        model_cfg = resolve_model(cfg, key)
        out_dir = f"saved_models/benchmark_{key}"
        print(f"\n{'='*70}\nBENCHMARK: {key} ({model_cfg['hf_name']})\n{'='*70}")

        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        start = time.perf_counter()
        try:
            metrics = train(model_key=key, epochs_override=epochs,
                            output_dir_override=out_dir, quiet=True)
        except Exception as e:
            print(f"[benchmark] {key} FAILED: {e}")
            results.append({"model_key": key, "hf_name": model_cfg["hf_name"],
                            "failed": str(e)})
            continue
        elapsed_min = (time.perf_counter() - start) / 60

        gpu_gb = (torch.cuda.max_memory_allocated() / 1024**3
                  if torch.cuda.is_available() else 0.0)
        per_lang = metrics.get("per_language", {})
        ar = per_lang.get("arabic", {})
        en = per_lang.get("english", {})
        row = {
            "model_key": key,
            "hf_name": model_cfg["hf_name"],
            "accuracy": metrics.get("eval_accuracy"),
            "precision": metrics.get("eval_precision"),
            "recall": metrics.get("eval_recall"),
            "f1": metrics.get("eval_f1"),
            "roc_auc": metrics.get("eval_roc_auc"),
            "f1_arabic": ar.get("f1"),
            "f1_english": en.get("f1"),
            "n_arabic": ar.get("n"),
            "train_minutes": round(elapsed_min, 1),
            "gpu_gb": round(gpu_gb, 2),
            "size_mb": round(_dir_size_mb(out_dir), 1),
            "latency_ms": round(_measure_inference_latency(out_dir), 1),
        }
        results.append(row)

    ok = [r for r in results if "failed" not in r]
    ok.sort(key=lambda r: (-(r["f1"] or 0), -(r["roc_auc"] or 0),
                            r["latency_ms"] or 1e9))
    winner = ok[0] if ok else None

    lines = ["# SMS Transformer Model Benchmark", "",
             "| Model | Acc | Prec | Rec | F1 | ROC-AUC | F1 (ar) | F1 (en) | "
             "Train (min) | GPU (GB) | Size (MB) | Latency (ms) |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        if "failed" in r:
            lines.append(f"| {r['model_key']} | FAILED: {r['failed'][:40]} "
                         "| | | | | | | | | | |")
            continue
        f1_ar = f"{r['f1_arabic']:.4f}" if r.get("f1_arabic") is not None else "n/a"
        f1_en = f"{r['f1_english']:.4f}" if r.get("f1_english") is not None else "n/a"
        lines.append(
            f"| {r['model_key']} | {r['accuracy']:.4f} | {r['precision']:.4f} "
            f"| {r['recall']:.4f} | {r['f1']:.4f} | {r['roc_auc']:.4f} "
            f"| {f1_ar} | {f1_en} "
            f"| {r['train_minutes']} | {r['gpu_gb']} | {r['size_mb']} "
            f"| {r['latency_ms']} |")

    if winner:
        lines += ["", f"## Recommendation: **{winner['model_key']}** "
                      f"({winner['hf_name']})",
                  "", "Selected on highest overall F1, ties broken by ROC-AUC "
                      "then inference latency."]
        # Honesty check: is the margin actually meaningful?
        if len(ok) > 1:
            margin = (ok[0]["f1"] or 0) - (ok[1]["f1"] or 0)
            n_eval = (ok[0].get("n_arabic") or 0) + (ok[0].get("f1_english")
                                                      is not None) * 0
            if margin < 0.01:
                lines += ["", "> **Caveat: the margin is within noise.** The top "
                          f"models differ by {margin:.4f} F1 -- on an eval set this "
                          "size that is a handful of messages, and a different "
                          "random seed could reorder them. Do not claim one model "
                          "is definitively better. Consider the per-language "
                          "columns and operational factors (size, latency, "
                          "checkpoint stability) instead."]
        if winner.get("f1_arabic") is not None and winner.get("f1_english") is not None:
            gap = winner["f1_english"] - winner["f1_arabic"]
            if abs(gap) >= 0.03:
                worse = "Arabic" if gap > 0 else "English"
                lines += ["", f"> **Language gap:** {worse} F1 is "
                          f"{abs(gap):.3f} lower than the other language for the "
                          "recommended model. The headline F1 hides this."]
        lines += ["", f"To adopt it: set `selected_model: {winner['model_key']}` "
                  f"in config/training_config.yaml and run "
                  f"`python sms_model/train_transformer.py` for a full-length "
                  f"training run (benchmark runs use only {epochs} epochs)."]

    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    print(f"\nReport saved to {report_path}")
    return results


if __name__ == "__main__":
    run_benchmark()
