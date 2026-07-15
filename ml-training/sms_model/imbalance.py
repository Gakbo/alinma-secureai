"""
Automatic class-imbalance handling (upgrade requirement #4).

Measures the imbalance ratio and picks the mildest strategy that fixes it:

  ratio < 1.5x   -> "none"            (already balanced)
  1.5x - 10x     -> "class_weights"   (loss reweighting; no data duplication)
  > 10x          -> "oversample"      (duplicate minority) + class_weights

Rationale: class weights are always safe (no synthetic rows, no lost data).
Oversampling only kicks in for severe imbalance where weights alone tend to
under-train the minority. Undersampling is available but never auto-chosen,
because throwing away majority data is rarely right for small SMS corpora.
Focal loss is intentionally NOT auto-selected: on datasets of this size it
adds a tunable hyperparameter (gamma) with unstable benefit; class weights
achieve the same goal predictably.
"""
import numpy as np
import pandas as pd


def measure_imbalance(labels: pd.Series) -> dict:
    counts = labels.value_counts()
    majority, minority = counts.max(), counts.min()
    ratio = float(majority) / max(int(minority), 1)
    return {
        "counts": counts.to_dict(),
        "majority": int(majority),
        "minority": int(minority),
        "ratio": round(ratio, 2),
    }


def choose_strategy(labels: pd.Series, configured: str = "auto") -> dict:
    info = measure_imbalance(labels)
    if configured != "auto":
        strategy = configured
    elif info["ratio"] < 1.5:
        strategy = "none"
    elif info["ratio"] <= 10:
        strategy = "class_weights"
    else:
        strategy = "oversample"
    info["strategy"] = strategy
    return info


def compute_class_weights(labels: pd.Series) -> dict:
    """Balanced weights: n_samples / (n_classes * count_c). Keyed by label."""
    counts = labels.value_counts()
    n, k = len(labels), len(counts)
    return {label: float(n / (k * c)) for label, c in counts.items()}


def apply_oversample(df: pd.DataFrame, label_col: str = "label",
                     seed: int = 42) -> pd.DataFrame:
    """Random-duplicate minority rows up to majority size (training split only)."""
    counts = df[label_col].value_counts()
    majority_n = counts.max()
    parts = []
    rng = np.random.RandomState(seed)
    for label, n in counts.items():
        subset = df[df[label_col] == label]
        if n < majority_n:
            extra = subset.sample(majority_n - n, replace=True, random_state=rng)
            subset = pd.concat([subset, extra])
        parts.append(subset)
    return pd.concat(parts).sample(frac=1, random_state=seed).reset_index(drop=True)


def apply_undersample(df: pd.DataFrame, label_col: str = "label",
                      seed: int = 42) -> pd.DataFrame:
    """Downsample majority to minority size. Available but not auto-chosen."""
    counts = df[label_col].value_counts()
    minority_n = counts.min()
    parts = [
        df[df[label_col] == label].sample(minority_n, random_state=seed)
        for label in counts.index
    ]
    return pd.concat(parts).sample(frac=1, random_state=seed).reset_index(drop=True)


def prepare_training_frame(train_df: pd.DataFrame, configured: str = "auto",
                           seed: int = 42):
    """
    Returns (possibly-resampled train_df, class_weights_or_None, info_dict).
    Applied ONLY to the training split -- never to eval data.
    """
    info = choose_strategy(train_df["label"], configured)
    weights = None
    out = train_df

    if info["strategy"] in ("class_weights", "oversample"):
        weights = compute_class_weights(train_df["label"])
    if info["strategy"] == "oversample":
        out = apply_oversample(train_df, seed=seed)
        # Recompute weights after resampling (they'll be ~equal now).
        weights = compute_class_weights(out["label"])
    if info["strategy"] == "undersample":
        out = apply_undersample(train_df, seed=seed)

    print(f"[imbalance] counts={info['counts']} ratio={info['ratio']}x "
          f"-> strategy={info['strategy']}"
          + (f", class_weights={ {k: round(v,3) for k,v in weights.items()} }"
             if weights else ""))
    return out, weights, info
