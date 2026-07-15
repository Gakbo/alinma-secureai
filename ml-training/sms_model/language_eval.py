"""
Per-language evaluation (Arabic / English / mixed).

Why this exists: a single headline accuracy hides the thing you actually
care about. With SMS Spam Collection (5,572 English) dwarfing the Arabic
set (494), an overall "99% accuracy" is mostly measuring English generic
spam -- it says almost nothing about Arabic bank phishing, which is the
actual threat Alinma SecureAI targets.

This module segments the eval set by script and reports metrics for each,
so you can answer "how does it do on Arabic specifically?" with a number
instead of a guess.

Language buckets (detected from the message text itself):
    arabic  -- Arabic chars present, no meaningful Latin content
    english -- Latin chars present, no Arabic
    mixed   -- both scripts present (code-switched)
"""
import re

import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, precision_recall_fscore_support,
                             roc_auc_score, confusion_matrix)

_ARABIC_START, _ARABIC_END = "\u0600", "\u06ff"

# URLs are stripped before language detection: an Arabic scam SMS routinely
# carries "http://alinma-verify.xyz", and those Latin characters say nothing
# about the language the message is written in.
_URL_RE = re.compile(r"(https?://\S+|www\.\S+|\b\S+\.(?:com|net|org|xyz|top|info|click|sa)\b)",
                     re.IGNORECASE)
# A "Latin word" = 2+ consecutive Latin letters. Counting words rather than
# letters stops a lone token like "SAR" or "OTP" from making an otherwise
# Arabic message look code-switched.
_LATIN_WORD_RE = re.compile(r"[A-Za-z]{2,}")


def _has_arabic(text: str) -> bool:
    return any(_ARABIC_START <= ch <= _ARABIC_END for ch in str(text))


def _latin_word_count(text: str) -> int:
    return len(_LATIN_WORD_RE.findall(_URL_RE.sub(" ", str(text))))


def detect_language(text: str, min_latin_words: int = 2) -> str:
    """
    Bucket a message as 'arabic' | 'english' | 'mixed'.

    Only counts Latin words OUTSIDE urls, and requires at least
    `min_latin_words` of them before calling a message code-switched --
    otherwise "تم تحويل SAR 500" or an Arabic SMS containing a link would
    be misfiled as 'mixed'.
    """
    text = str(text)
    arabic = _has_arabic(text)
    latin_words = _latin_word_count(text)
    if arabic and latin_words >= min_latin_words:
        return "mixed"
    if arabic:
        return "arabic"
    return "english"


def _metrics_for(y_true: np.ndarray, y_pred: np.ndarray,
                 y_prob: np.ndarray) -> dict:
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", zero_division=0)
    out = {
        "n": int(len(y_true)),
        "n_phishing": int((y_true == 1).sum()),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
    }
    # ROC-AUC is undefined when only one class is present in the slice.
    out["roc_auc"] = (float(roc_auc_score(y_true, y_prob))
                      if len(np.unique(y_true)) > 1 else None)
    tn, fp, fn, tp = (confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
                      if len(y_true) else (0, 0, 0, 0))
    out["false_alarms"] = int(fp)     # safe wrongly flagged as phishing
    out["missed_scams"] = int(fn)     # phishing wrongly cleared as safe
    return out


def evaluate_by_language(messages, y_true, y_prob, threshold: float = 0.5,
                         min_slice: int = 15) -> dict:
    """
    messages : iterable of raw SMS strings (the eval split, same order)
    y_true   : 0/1 ground truth  (1 = phishing)
    y_prob   : predicted probability of class 1
    Returns {"overall": {...}, "arabic": {...}, "english": {...}, "mixed": {...}}
    Slices smaller than min_slice are reported but flagged as unreliable.
    """
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    y_pred = (y_prob >= threshold).astype(int)
    langs = np.array([detect_language(m) for m in messages])

    results = {"overall": _metrics_for(y_true, y_pred, y_prob)}
    for lang in ("arabic", "english", "mixed"):
        mask = langs == lang
        if mask.sum() == 0:
            continue
        slice_metrics = _metrics_for(y_true[mask], y_pred[mask], y_prob[mask])
        slice_metrics["reliable"] = bool(mask.sum() >= min_slice)
        results[lang] = slice_metrics
    return results


def format_report(results: dict, model_name: str = "") -> str:
    lines = []
    header = f"PER-LANGUAGE EVALUATION{f' -- {model_name}' if model_name else ''}"
    lines.append("=" * 78)
    lines.append(header)
    lines.append("=" * 78)
    lines.append(f"{'slice':<10}{'n':>6}{'phish':>7}{'acc':>8}{'prec':>8}"
                 f"{'rec':>8}{'F1':>8}{'AUC':>8}{'FA':>5}{'miss':>6}")
    lines.append("-" * 78)
    for key in ("overall", "arabic", "english", "mixed"):
        r = results.get(key)
        if not r:
            continue
        auc = f"{r['roc_auc']:.4f}" if r["roc_auc"] is not None else "  n/a"
        flag = "" if r.get("reliable", True) else "  <- too few to trust"
        lines.append(
            f"{key:<10}{r['n']:>6}{r['n_phishing']:>7}{r['accuracy']:>8.4f}"
            f"{r['precision']:>8.4f}{r['recall']:>8.4f}{r['f1']:>8.4f}"
            f"{auc:>8}{r['false_alarms']:>5}{r['missed_scams']:>6}{flag}")
    lines.append("-" * 78)
    lines.append("FA = false alarms (safe flagged as phishing) | "
                 "miss = missed scams (phishing cleared as safe)")
    ar = results.get("arabic")
    en = results.get("english")
    if ar and en and ar.get("reliable") and en.get("reliable"):
        gap = en["f1"] - ar["f1"]
        if abs(gap) >= 0.03:
            worse = "Arabic" if gap > 0 else "English"
            lines.append(f"NOTE: {worse} F1 is {abs(gap):.3f} lower -- the "
                         f"headline number hides this gap.")
    lines.append("=" * 78)
    return "\n".join(lines)
