"""
Optional data augmentation for SMS text (upgrade requirement #5).

Deliberately CONSERVATIVE:
  - OFF by default (config: augmentation.enabled)
  - applied only to the TRAINING split, never eval
  - augmented rows are ADDED, originals are never modified
  - capped by max_augmented_ratio so synthetic text can't dominate
  - minority-class only by default (that's where extra data helps)

Implemented techniques (dependency-free, Arabic + English aware):
  char_noise       - one keyboard-adjacent typo per message (EN) or a
                     single-character swap (AR), mimicking real typos
  word_swap        - swap two adjacent words once
  random_deletion  - delete one non-critical token (skips URLs/numbers)

Heavier techniques from the wishlist (back-translation, paraphrasing,
context-aware augmentation) are intentionally NOT implemented here: they
need external models/APIs, are slow, and on a ~1k-row corpus they risk
label drift (a paraphrased scam can stop reading like a scam). If the
corpus grows 10x, revisit. Never reduce dataset quality (requirement).
"""
import random
import re

import pandas as pd

_EN_ADJACENT = {
    "a": "qs", "b": "vn", "c": "xv", "d": "sf", "e": "wr", "f": "dg",
    "g": "fh", "h": "gj", "i": "uo", "j": "hk", "k": "jl", "l": "k",
    "m": "n", "n": "bm", "o": "ip", "p": "o", "q": "wa", "r": "et",
    "s": "ad", "t": "ry", "u": "yi", "v": "cb", "w": "qe", "x": "zc",
    "y": "tu", "z": "x",
}
_URL_OR_NUM = re.compile(r"(https?://\S+|www\.\S+|\d+)")


def _is_protected(token: str) -> bool:
    return bool(_URL_OR_NUM.search(token))


def char_noise(text: str, rng: random.Random) -> str:
    chars = list(text)
    idxs = [i for i, c in enumerate(chars) if c.lower() in _EN_ADJACENT
            or "\u0600" <= c <= "\u06FF"]
    if not idxs:
        return text
    i = rng.choice(idxs)
    c = chars[i]
    if c.lower() in _EN_ADJACENT:
        repl = rng.choice(_EN_ADJACENT[c.lower()])
        chars[i] = repl.upper() if c.isupper() else repl
    else:
        # Arabic: swap with neighbor character (simple realistic slip).
        j = i + 1 if i + 1 < len(chars) else i - 1
        chars[i], chars[j] = chars[j], chars[i]
    return "".join(chars)


def word_swap(text: str, rng: random.Random) -> str:
    words = text.split()
    if len(words) < 4:
        return text
    i = rng.randrange(len(words) - 1)
    if _is_protected(words[i]) or _is_protected(words[i + 1]):
        return text
    words[i], words[i + 1] = words[i + 1], words[i]
    return " ".join(words)


def random_deletion(text: str, rng: random.Random) -> str:
    words = text.split()
    if len(words) < 5:
        return text
    candidates = [i for i, w in enumerate(words) if not _is_protected(w)]
    if not candidates:
        return text
    del words[rng.choice(candidates)]
    return " ".join(words)


_TECHNIQUES = {
    "char_noise": char_noise,
    "word_swap": word_swap,
    "random_deletion": random_deletion,
}


def augment_training_frame(train_df: pd.DataFrame, aug_cfg: dict,
                           seed: int = 42) -> pd.DataFrame:
    """Return train_df + augmented rows per config. No-op when disabled."""
    if not aug_cfg or not aug_cfg.get("enabled"):
        return train_df

    enabled = [name for name, on in (aug_cfg.get("techniques") or {}).items()
               if on and name in _TECHNIQUES]
    if not enabled:
        return train_df

    rng = random.Random(seed)
    counts = train_df["label"].value_counts()
    minority_label = counts.idxmin()
    source = (train_df[train_df["label"] == minority_label]
              if aug_cfg.get("minority_only", True) else train_df)

    cap = int(len(source) * float(aug_cfg.get("max_augmented_ratio", 0.5)))
    if cap <= 0:
        return train_df

    rows = []
    pool = source.sample(frac=1, random_state=seed)
    for _, row in pool.iterrows():
        if len(rows) >= cap:
            break
        technique = _TECHNIQUES[rng.choice(enabled)]
        new_text = technique(str(row["message"]), rng)
        if new_text != row["message"]:
            rows.append({"message": new_text, "label": row["label"]})

    if not rows:
        return train_df
    aug_df = pd.DataFrame(rows).drop_duplicates(subset="message")
    # Never collide with existing messages (keeps eval leakage impossible).
    aug_df = aug_df[~aug_df["message"].isin(train_df["message"])]
    print(f"[augment] +{len(aug_df)} rows via {enabled} "
          f"(minority='{minority_label}', cap={cap})")
    return pd.concat([train_df, aug_df], ignore_index=True)
