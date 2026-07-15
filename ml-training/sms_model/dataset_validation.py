"""
Dataset validation pipeline (upgrade requirement #3).

Runs BEFORE training. Checks every registered dataset for:
  - missing columns          - invalid labels
  - missing values           - empty messages
  - wrong encodings          - duplicates (within and across datasets)
  - label distribution       - dataset statistics & quality warnings

Produces a human-readable report and a machine-readable summary.
Training aborts on hard errors when validation.fail_on_error is true.
"""
import os
from dataclasses import dataclass, field

import pandas as pd

from sms_datasets import DATASETS, DATA_DIR, _load_one

# Arabic Unicode block (U+0600-U+06FF), checked in pure Python so no regex
# engine (Python re vs PyArrow RE2) can disagree about escape syntax.
_ARABIC_START, _ARABIC_END = "\u0600", "\u06ff"


def _has_arabic(text: str) -> bool:
    return any(_ARABIC_START <= ch <= _ARABIC_END for ch in str(text))


@dataclass
class DatasetReport:
    name: str
    status: str = "ok"              # ok | warning | error | missing
    rows: int = 0
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    label_counts: dict = field(default_factory=dict)
    stats: dict = field(default_factory=dict)


def validate_one(cfg) -> DatasetReport:
    rep = DatasetReport(name=cfg.name)
    path = os.path.join(DATA_DIR, cfg.filename)

    if not os.path.exists(path):
        rep.status = "missing"
        rep.warnings.append(f"File not found: {path} (dataset skipped)")
        return rep

    # 1. Encoding check -- try declared encoding, then fallbacks.
    raw = None
    tried = []
    for enc in dict.fromkeys([cfg.encoding, "utf-8", "utf-8-sig", "latin-1"]):
        try:
            raw = pd.read_csv(path, encoding=enc)
            if enc != cfg.encoding:
                rep.warnings.append(
                    f"Declared encoding '{cfg.encoding}' failed; file read with "
                    f"'{enc}'. Update the registry entry."
                )
            break
        except Exception as e:
            tried.append(f"{enc}: {type(e).__name__}")
    if raw is None:
        rep.status = "error"
        rep.errors.append(f"Unreadable with any encoding ({'; '.join(tried)})")
        return rep

    if cfg.pre_rename:
        raw = raw.rename(columns=cfg.pre_rename)

    # 2. Column checks.
    for col in (cfg.message_col, cfg.label_col):
        if col not in raw.columns:
            rep.status = "error"
            rep.errors.append(
                f"Missing column '{col}'. Actual columns: {list(raw.columns)}"
            )
    if rep.errors:
        return rep

    df = raw[[cfg.message_col, cfg.label_col]].copy()
    df.columns = ["message", "label"]
    rep.rows = len(df)

    # 3. Missing values.
    n_null_msg = df["message"].isna().sum()
    n_null_lbl = df["label"].isna().sum()
    if n_null_msg:
        rep.warnings.append(f"{n_null_msg} rows with missing message (will be dropped)")
    if n_null_lbl:
        rep.warnings.append(f"{n_null_lbl} rows with missing label (will be dropped)")

    # 4. Empty / whitespace-only messages.
    df["message"] = df["message"].astype(str)
    n_empty = (df["message"].str.strip() == "").sum()
    if n_empty:
        rep.warnings.append(f"{n_empty} empty/whitespace-only messages (will be dropped)")

    # 5. Invalid labels -- anything the label_map can't normalize.
    norm = {str(k).strip().lower(): v for k, v in cfg.label_map.items()}
    mapped = df["label"].map(lambda x: norm.get(str(x).strip().lower()))
    n_invalid = mapped.isna().sum() - n_null_lbl
    if n_invalid > 0:
        bad_values = (
            df.loc[mapped.isna() & df["label"].notna(), "label"]
            .astype(str).value_counts().head(5).to_dict()
        )
        rep.warnings.append(
            f"{n_invalid} rows with labels not covered by label_map "
            f"(examples: {bad_values}) -- they will be dropped"
        )

    # 6. Duplicates within the dataset.
    n_dup = df.duplicated(subset="message").sum()
    if n_dup:
        rep.warnings.append(f"{n_dup} duplicate messages within this dataset")

    # 7. Label distribution + stats on the valid subset.
    valid = df[mapped.notna()].copy()
    valid["label"] = mapped[mapped.notna()]
    rep.label_counts = valid["label"].value_counts().to_dict()
    if valid.empty:
        rep.status = "error"
        rep.errors.append("No valid rows after label mapping")
        return rep

    lengths = valid["message"].str.len()
    # Arabic-share stat.
    # NOTE: deliberately NOT using .str.contains() with a regex here.
    # pandas 3.x backs strings with PyArrow, whose RE2 engine rejects "\u"
    # escape sequences ("ArrowInvalid: invalid escape sequence: \u"), and
    # engine behaviour varies by pandas/pyarrow version. A plain Python
    # predicate is engine-independent and always correct. Cost is negligible
    # at validation scale.
    arabic_share = float(valid["message"].map(_has_arabic).mean())
    rep.stats = {
        "valid_rows": int(len(valid)),
        "avg_message_chars": round(float(lengths.mean()), 1),
        "min_message_chars": int(lengths.min()),
        "max_message_chars": int(lengths.max()),
        "arabic_share": round(arabic_share, 3),
    }

    if len(valid) < 100:
        rep.warnings.append(f"Small dataset ({len(valid)} valid rows)")
    if len(rep.label_counts) == 1:
        rep.warnings.append("Single-class dataset -- contributes no contrast on its own")

    if rep.warnings and rep.status == "ok":
        rep.status = "warning"
    return rep


def validate_all(report_path: str = None, fail_on_error: bool = True):
    reports = [validate_one(cfg) for cfg in DATASETS]

    # Cross-dataset duplicate check on datasets that loaded.
    frames = []
    for cfg in DATASETS:
        df = _load_one(cfg)
        if df is not None and len(df):
            df = df.copy()
            df["_source"] = cfg.name
            frames.append(df)
    cross_dup = 0
    if len(frames) > 1:
        merged = pd.concat(frames, ignore_index=True)
        cross_dup = int(merged.duplicated(subset="message").sum())

    lines = ["=" * 70, "DATASET VALIDATION REPORT", "=" * 70]
    hard_errors = 0
    total_rows = 0
    label_totals = {}
    for r in reports:
        lines.append(f"\n[{r.status.upper():7s}] {r.name}")
        if r.rows:
            lines.append(f"  rows read: {r.rows}")
        for k, v in r.stats.items():
            lines.append(f"  {k}: {v}")
        if r.label_counts:
            lines.append(f"  labels: {r.label_counts}")
            for k, v in r.label_counts.items():
                label_totals[k] = label_totals.get(k, 0) + v
            total_rows += r.stats.get("valid_rows", 0)
        for w in r.warnings:
            lines.append(f"  ! {w}")
        for e in r.errors:
            lines.append(f"  X {e}")
            hard_errors += 1

    lines.append("\n" + "-" * 70)
    lines.append(f"TOTAL valid rows across datasets: {total_rows}")
    lines.append(f"Combined label distribution: {label_totals}")
    lines.append(f"Cross-dataset duplicate messages: {cross_dup} (deduplicated at merge)")
    if label_totals:
        counts = sorted(label_totals.values())
        if len(counts) > 1 and counts[0] > 0:
            ratio = counts[-1] / counts[0]
            lines.append(f"Imbalance ratio (majority/minority): {ratio:.2f}x")
    lines.append("=" * 70)

    text = "\n".join(lines)
    print(text)
    if report_path:
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"\nReport saved to {report_path}")

    if hard_errors and fail_on_error:
        raise SystemExit(
            f"Validation found {hard_errors} hard error(s). Fix them or set "
            f"validation.fail_on_error: false in the config to continue anyway."
        )
    return reports


if __name__ == "__main__":
    validate_all(report_path=os.path.join("saved_models", "dataset_validation_report.txt"),
                 fail_on_error=False)
