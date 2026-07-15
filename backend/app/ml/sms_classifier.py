"""
Model A: SMS Phishing / Scam Classifier.

ARCHITECTURE
------------
Two layers, deliberately separated:

  1. SCORE  -- produced by the fine-tuned XLM-RoBERTa model
               (trained by ml-training/sms_model/train_transformer.py).
  2. REASON -- produced by the transparent keyword/URL rule engine below.

Why both? The model gives an accurate score but cannot say *why*. Telling a
customer "87.3% phishing probability" is useless; telling them "flagged
because it impersonates Alinma Bank and contains an unrecognized link" is
actionable. The rules supply that human-readable reasoning, which is FR7
(AI Explanation Engine). The model decides; the rules explain.

MODEL BACKEND (env var MODEL_BACKEND):
    auto        (default) -- use the transformer if it loads, else rules
    transformer           -- require the transformer; error if unavailable
    rules                 -- force the rule engine (no torch needed)

Graceful degradation is intentional: if the model folder is missing (a
teammate cloned the repo without the 1.1GB artifact) or torch isn't
installed, the API keeps working on rules rather than 500-ing. Check the
startup log to see which backend is live -- never assume.

MODEL PATH: backend/saved_models/transformer_sms_classifier/
Copy it there after training with scripts/copy_model.ps1
"""
import logging
import os
import re
import threading
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_DIR = os.getenv(
    "SMS_MODEL_DIR",
    os.path.join(_BACKEND_DIR, "saved_models", "transformer_sms_classifier"),
)
MODEL_BACKEND = os.getenv("MODEL_BACKEND", "auto").lower()

# Decision thresholds on P(phishing), 0-100.
# NOTE: the model was evaluated at a 0.50 binary cutoff (F1 0.9683).
# Here "not safe" starts at 35 rather than 50 -- deliberately biased toward
# warning, because for fraud PREVENTION a false alarm costs a moment of
# friction while a missed scam costs money. The 35-70 band surfaces as
# "suspicious" (warn, don't block). Tune via env vars if needed.
FRAUD_THRESHOLD = float(os.getenv("SMS_FRAUD_THRESHOLD", "70"))
SUSPICIOUS_THRESHOLD = float(os.getenv("SMS_SUSPICIOUS_THRESHOLD", "35"))

# ---------------------------------------------------------------------------
# Rule engine -- powers explanations (and the fallback score)
# ---------------------------------------------------------------------------
SUSPICIOUS_KEYWORDS_EN = [
    "verify your account", "account will be blocked", "account will be suspended",
    "click here", "click the link", "confirm your identity", "urgent action required",
    "update your information", "your card has been", "unusual activity",
    "winner", "prize", "free gift", "limited time", "act now",
]

SUSPICIOUS_KEYWORDS_AR = [
    "تأكيد الحساب", "سيتم إيقاف", "سيتم حظر", "انقر هنا", "تحديث بياناتك",
    "حسابك سيتم تعليقه", "تحقق من حسابك", "جائزة", "مكافأة", "عاجل",
]

BANK_IMPERSONATION_TERMS = ["alinma", "الإنماء", "بنك الإنماء"]

URL_PATTERN = re.compile(
    r"(https?://\S+|www\.\S+|bit\.ly/\S+|\S+\.(xyz|top|click|info)\b)", re.IGNORECASE)

TRUSTED_DOMAINS = ["alinma.sa", "alinma.com"]


@dataclass
class SMSClassificationResult:
    classification: str          # "safe" | "suspicious" | "fraud"
    risk_score: float            # 0-100
    explanation: str
    suspicious_keywords: list = field(default_factory=list)
    contains_suspicious_url: bool = False


def _find_keywords(text: str) -> list:
    text_lower = text.lower()
    found = [kw for kw in SUSPICIOUS_KEYWORDS_EN if kw in text_lower]
    found += [kw for kw in SUSPICIOUS_KEYWORDS_AR if kw in text]
    return found


def _has_suspicious_url(text: str) -> bool:
    if not URL_PATTERN.search(text):
        return False
    for m in URL_PATTERN.finditer(text):
        url = m.group(0).lower()
        if any(domain in url for domain in TRUSTED_DOMAINS):
            continue
        return True
    return False


def _mentions_bank_brand(text: str) -> bool:
    text_lower = text.lower()
    return any(term.lower() in text_lower for term in BANK_IMPERSONATION_TERMS)


def _rule_score(keywords_found: list, has_url: bool, impersonates: bool) -> float:
    score = min(len(keywords_found), 4) * 15.0
    score += 25 if has_url else 0
    score += 15 if (impersonates and (keywords_found or has_url)) else 0
    return min(score, 100.0)


def _build_explanation(classification: str, keywords_found: list, has_url: bool,
                       impersonates: bool, score: float, model_used: bool) -> str:
    if classification == "safe":
        return "No suspicious patterns found in this message."

    reasons = []
    if impersonates and (keywords_found or has_url):
        reasons.append("it impersonates Alinma Bank branding")
    if keywords_found:
        reasons.append(f"it contains urgency/scam phrasing ({', '.join(keywords_found[:3])})")
    if has_url:
        reasons.append("it contains an unrecognized or shortened link")

    if not reasons:
        # The model flagged it but no rule fired -- say so honestly rather
        # than inventing a reason the evidence doesn't support.
        if model_used:
            return (f"The AI model rates this {score:.0f}/100 for phishing risk based on "
                    f"patterns learned from real scam messages, though it does not match "
                    f"our known keyword or link indicators. Treat with caution.")
        return "This message shows weak phishing indicators. Treat with caution."

    prefix = (f"The AI model rates this {score:.0f}/100 for phishing risk. Flagged because "
              if model_used else "This message is flagged because ")
    return prefix + "; ".join(reasons) + "."


# ---------------------------------------------------------------------------
# Transformer backend (lazy-loaded singleton)
# ---------------------------------------------------------------------------
class _TransformerModel:
    """Loads XLM-R once, on first use. Thread-safe. CPU inference is fine."""

    _instance: Optional["_TransformerModel"] = None
    _lock = threading.Lock()
    _load_failed = False

    def __init__(self):
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification

        self._torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
        self.model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
        self.model.eval()
        # GPU if present, else CPU. CPU latency is ~50-200ms per SMS, well
        # inside the <2s requirement -- no GPU needed in production.
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        logger.info("SMS classifier: loaded transformer from %s on %s",
                    MODEL_DIR, self.device)

    @classmethod
    def get(cls) -> Optional["_TransformerModel"]:
        if cls._load_failed:
            return None
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None and not cls._load_failed:
                    try:
                        cls._instance = cls()
                    except Exception as e:
                        cls._load_failed = True
                        logger.warning(
                            "SMS classifier: transformer unavailable (%s). "
                            "Falling back to the rule engine. Expected model at %s",
                            e, MODEL_DIR)
                        return None
        return cls._instance

    def predict_proba(self, message: str) -> float:
        """Returns P(phishing) in [0, 1]."""
        inputs = self.tokenizer(message, truncation=True, padding=True,
                                max_length=128, return_tensors="pt").to(self.device)
        with self._torch.no_grad():
            logits = self.model(**inputs).logits
        return float(self._torch.softmax(logits, dim=1)[0, 1].item())


def model_status() -> dict:
    """Which backend is actually serving? Call at startup and log it."""
    if MODEL_BACKEND == "rules":
        return {"backend": "rules", "reason": "forced by MODEL_BACKEND=rules"}
    m = _TransformerModel.get()
    if m is not None:
        return {"backend": "transformer", "model_dir": MODEL_DIR, "device": m.device}
    if MODEL_BACKEND == "transformer":
        raise RuntimeError(
            f"MODEL_BACKEND=transformer but the model could not be loaded from "
            f"{MODEL_DIR}. Run ml-training/sms_model/train_transformer.py and "
            f"copy the output, or set MODEL_BACKEND=rules.")
    return {"backend": "rules", "reason": f"transformer unavailable at {MODEL_DIR}"}


# ---------------------------------------------------------------------------
# Public API -- signature unchanged, so routers/sms.py needs no edits.
# ---------------------------------------------------------------------------
def classify_sms(message: str) -> SMSClassificationResult:
    keywords_found = _find_keywords(message)
    has_url = _has_suspicious_url(message)
    impersonates = _mentions_bank_brand(message)

    score = None
    model_used = False
    if MODEL_BACKEND != "rules":
        model = _TransformerModel.get()
        if model is not None:
            try:
                score = model.predict_proba(message) * 100.0
                model_used = True
            except Exception as e:
                logger.error("SMS classifier: inference failed (%s); using rules", e)

    if score is None:
        if MODEL_BACKEND == "transformer":
            raise RuntimeError(f"Transformer required but unavailable ({MODEL_DIR})")
        score = _rule_score(keywords_found, has_url, impersonates)

    if score >= FRAUD_THRESHOLD:
        classification = "fraud"
    elif score >= SUSPICIOUS_THRESHOLD:
        classification = "suspicious"
    else:
        classification = "safe"

    return SMSClassificationResult(
        classification=classification,
        risk_score=round(score, 1),
        explanation=_build_explanation(classification, keywords_found, has_url,
                                        impersonates, score, model_used),
        suspicious_keywords=keywords_found,
        contains_suspicious_url=has_url,
    )
