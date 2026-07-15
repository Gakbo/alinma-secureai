"""
AI Explanation Engine (FR7).

Takes the raw outputs from the SMS classifier / transaction risk engine
and produces a single human-readable, non-technical explanation string.
Both ml modules already generate their own `explanation` field — this
module exists for cases where you want to combine multiple signals
(e.g. transaction + device + behavior) into one unified message.
"""
from typing import Optional


def build_explanation(reasons: list[str], subject: str = "This activity") -> str:
    if not reasons:
        return f"{subject} matches expected, normal behavior."
    if len(reasons) == 1:
        return f"{subject} is flagged because {reasons[0]}."
    return f"{subject} is flagged because " + "; ".join(reasons) + "."


def combine_explanations(*explanations: Optional[str]) -> str:
    """Merge multiple non-empty explanation strings into one paragraph."""
    parts = [e.strip().rstrip(".") for e in explanations if e]
    if not parts:
        return "No risk indicators detected."
    return ". ".join(parts) + "."
