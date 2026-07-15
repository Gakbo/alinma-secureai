"""
Model C: Behavior Anomaly Detection.

MVP implementation: simple statistical outlier check (z-score against the
user's own recent history) standing in for Isolation Forest.

Swap-in path:
    - Collect a feature matrix per user over time (login hour, amount,
      device changes, location).
    - Fit `sklearn.ensemble.IsolationForest` on historical data.
    - Replace `is_anomalous_amount()` body with `model.predict(...)`.
"""
from statistics import mean, pstdev
from typing import Sequence


def is_anomalous_amount(amount: float, history: Sequence[float], z_threshold: float = 2.5) -> tuple[bool, float]:
    """
    Returns (is_anomalous, z_score) comparing `amount` against the user's
    transaction history. With too little history, falls back to a simple
    multiple-of-average check.
    """
    if len(history) < 3:
        avg = mean(history) if history else 0.0
        if avg == 0:
            return False, 0.0
        ratio = amount / avg
        return ratio > 3, ratio

    avg = mean(history)
    std = pstdev(history) or 1.0
    z = (amount - avg) / std
    return z > z_threshold, round(z, 2)


def device_switch_flag(known_device_ids: Sequence[str], current_device_id: str) -> bool:
    """True if the current device has never been seen for this user before."""
    return current_device_id not in known_device_ids
