"""
Model A: SMS Phishing / Scam Classifier.

ARCHITECTURE — three tiers, in priority order:
────────────────────────────────────────────────
  1. TRANSFORMER  — fine-tuned XLM-RoBERTa (1.1 GB, highest accuracy)
  2. TFIDF-ML     — TF-IDF char n-grams + Logistic Regression trained on
                    ~6 500 rows of Arabic + English SMS spam data.
                    Activates automatically when the transformer is absent.
  3. RULE ENGINE  — keyword / URL heuristics. Fallback of last resort, and
                    the source of human-readable *explanations* regardless
                    of which scoring tier is active.

Why all three?
  • The model gives an accurate score but cannot say *why*.
  • The rules supply the human-readable reasoning (FR7 — AI Explanation).
  • The TF-IDF tier closes the gap between a 1.1 GB transformer and bare
    rules, with zero extra dependencies beyond sklearn + joblib.

MODEL_BACKEND env var:
    auto        (default) — transformer → tfidf → rules
    transformer           — require transformer; error if missing
    tfidf                 — use TF-IDF ML model; skip transformer
    rules                 — rule engine only

Model paths:
    Transformer : backend/saved_models/transformer_sms_classifier/
    TF-IDF      : backend/saved_models/sms_ml/vectorizer.joblib
                  backend/saved_models/sms_ml/classifier.joblib
"""
import json
import logging
import os
import re
import threading
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRANSFORMER_DIR = os.getenv(
    "SMS_MODEL_DIR",
    os.path.join(_BACKEND_DIR, "saved_models", "transformer_sms_classifier"),
)
TFIDF_DIR = os.getenv(
    "SMS_TFIDF_DIR",
    os.path.join(_BACKEND_DIR, "saved_models", "sms_ml"),
)
MODEL_BACKEND = os.getenv("MODEL_BACKEND", "auto").lower()

FRAUD_THRESHOLD     = float(os.getenv("SMS_FRAUD_THRESHOLD", "70"))
SUSPICIOUS_THRESHOLD = float(os.getenv("SMS_SUSPICIOUS_THRESHOLD", "35"))


# ---------------------------------------------------------------------------
# Rule engine — explanations + last-resort scoring
# ---------------------------------------------------------------------------

# English urgency / scam indicators
SUSPICIOUS_KEYWORDS_EN = [
    "verify your account", "account will be blocked", "account will be suspended",
    "click here", "click the link", "confirm your identity", "urgent action required",
    "update your information", "your card has been", "unusual activity",
    "winner", "prize", "free gift", "limited time", "act now",
    "account suspended", "login attempt", "unauthorized access",
    "reset your password", "verify immediately", "claim here",
    "congratulations", "you have won", "your account will be",
    "cancel here", "cancel now", "stop transfer",
]

# Arabic scam / phishing indicators (sourced from dataset analysis)
SUSPICIOUS_KEYWORDS_AR = [
    # Account threats
    "سيتم إيقاف", "سيتم حظر", "سيتم تعليق", "سيتم إغلاق",
    "تم حظر", "تم إيقاف", "تم تعليق", "تم إغلاق",
    "حسابك محظور", "بطاقتك محظورة",
    # ATM / card blocking (common in Arabic SMS fraud)
    "بطاقة الصراف", "الصراف الآلي", "تحديث بياناتك", "تحديث البيانات",
    "تحديث الحساب", "تحديث بطاقة", "تحديث الكارت",
    # Urgency / calls to action
    "اتصل بنا", "اتصل الان", "اتصل فوراً", "على الفور",
    "انقر هنا", "اضغط هنا", "اضغط الآن",
    "أوقفه الآن", "أوقف التحويل", "لإيقاف التحويل",
    # Prizes / rewards
    "جائزة", "مكافأة", "ربحت", "فزت", "مبروك",
    "مئتي ألف", "ألف ريال", "مليون",
    # Verification / identity
    "تأكيد الحساب", "تحقق من هويتك", "تحقق من حسابك",
    "التحقق الفوري", "تحقق فوراً",
    # Suspicious link prompts
    "عبر الرابط", "من خلال الرابط", "اضغط على الرابط",
    # Bank impersonation phrases
    "حسابك في الراجحي", "مصرف الراجحي", "البنك الأهلي",
    "سيتم إيقاف خدمة", "لإعادة تفعيل", "لتنشيط الحساب",
    # Unusual activity
    "نشاط غير معتاد", "نشاط مريب", "دخول غير مصرح",
]

# Bank / brand impersonation terms (Alinma + other Saudi banks commonly spoofed)
BANK_IMPERSONATION_TERMS = [
    "alinma", "الإنماء", "بنك الإنماء",
    "الراجحي", "الأهلي", "البنك الأهلي", "ساب", "riyad bank",
]

# URL / link detection
URL_PATTERN = re.compile(
    r"(https?://\S+|www\.\S+|bit\.ly/\S+|t\.ly/\S+|tinyurl\.\S+"
    r"|\S+\.(xyz|top|click|info|online|site|icu|shop)\b"
    r"|[a-z0-9\-]+\.(000webhostapp|repl\.co)\S*)",
    re.IGNORECASE,
)

# Phone numbers embedded in SMS (strong spam signal in Arabic datasets)
PHONE_PATTERN = re.compile(r"(?<!\d)0[5-9]\d{8}(?!\d)")

TRUSTED_DOMAINS = ["alinma.sa", "alinma.com"]


@dataclass
class SMSClassificationResult:
    classification: str           # "safe" | "suspicious" | "fraud"
    risk_score: float             # 0-100
    explanation: str
    suspicious_keywords: list = field(default_factory=list)
    contains_suspicious_url: bool = False


# ── helpers ─────────────────────────────────────────────────────────────────

def _find_keywords(text: str) -> list:
    text_lower = text.lower()
    found = [kw for kw in SUSPICIOUS_KEYWORDS_EN if kw in text_lower]
    found += [kw for kw in SUSPICIOUS_KEYWORDS_AR if kw in text]
    return found


def _has_suspicious_url(text: str) -> bool:
    for m in URL_PATTERN.finditer(text):
        url = m.group(0).lower()
        if any(d in url for d in TRUSTED_DOMAINS):
            continue
        return True
    return False


def _has_embedded_phone(text: str) -> bool:
    return bool(PHONE_PATTERN.search(text))


def _mentions_bank_brand(text: str) -> bool:
    tl = text.lower()
    return any(t.lower() in tl for t in BANK_IMPERSONATION_TERMS)


def _rule_score(keywords_found: list, has_url: bool, impersonates: bool,
                has_phone: bool) -> float:
    score  = min(len(keywords_found), 5) * 12.0
    score += 25.0 if has_url else 0.0
    score += 12.0 if has_phone else 0.0
    score += 15.0 if (impersonates and (keywords_found or has_url)) else 0.0
    return min(score, 100.0)


def _build_explanation(classification: str, keywords_found: list,
                       has_url: bool, impersonates: bool,
                       score: float, backend: str) -> str:
    if classification == "safe":
        return "No suspicious patterns detected in this message."

    reasons = []
    if impersonates and (keywords_found or has_url):
        reasons.append("it impersonates a bank's branding")
    if keywords_found:
        reasons.append(
            f"it contains urgency/scam phrasing ({', '.join(keywords_found[:3])})")
    if has_url:
        reasons.append("it contains an unrecognized or shortened link")

    if not reasons:
        if backend != "rules":
            return (f"The AI model rates this {score:.0f}/100 for phishing risk "
                    f"based on patterns learned from real scam messages, "
                    f"though no single indicator stands out. Treat with caution.")
        return "This message shows weak phishing indicators. Treat with caution."

    tag = {
        "transformer": f"The transformer AI model rates this {score:.0f}/100.",
        "tfidf":       f"The ML classifier rates this {score:.0f}/100.",
        "rules":       "",
    }.get(backend, "")

    prefix = (f"{tag} Flagged because " if tag else "This message is flagged because ")
    return prefix + "; ".join(reasons) + "."


# ===========================================================================
# Transformer backend (lazy singleton — 1.1 GB, skipped if absent)
# ===========================================================================
class _TransformerModel:
    _instance: Optional["_TransformerModel"] = None
    _lock = threading.Lock()
    _load_failed = False

    def __init__(self):
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification

        self._torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(TRANSFORMER_DIR)
        self.model = AutoModelForSequenceClassification.from_pretrained(TRANSFORMER_DIR)
        self.model.eval()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        logger.info("SMS: transformer loaded from %s on %s", TRANSFORMER_DIR, self.device)

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
                            e, TRANSFORMER_DIR)
        return cls._instance

    def predict_proba(self, message: str) -> float:
        inputs = self.tokenizer(message, truncation=True, padding=True,
                                max_length=128, return_tensors="pt").to(self.device)
        with self._torch.no_grad():
            logits = self.model(**inputs).logits
        return float(self._torch.softmax(logits, dim=1)[0, 1].item())


# ===========================================================================
# TF-IDF ML backend (lazy singleton — ~5 MB, fast to load)
# ===========================================================================
class _TfidfModel:
    _instance: Optional["_TfidfModel"] = None
    _lock = threading.Lock()
    _load_failed = False

    def __init__(self):
        import joblib
        vec_path = os.path.join(TFIDF_DIR, "vectorizer.joblib")
        clf_path = os.path.join(TFIDF_DIR, "classifier.joblib")
        if not os.path.exists(vec_path) or not os.path.exists(clf_path):
            raise FileNotFoundError(
                f"TF-IDF model files not found in {TFIDF_DIR}. "
                "Run: python backend/train_models.py")
        self.vectorizer = joblib.load(vec_path)
        self.clf = joblib.load(clf_path)

        meta_path = os.path.join(TFIDF_DIR, "meta.json")
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                meta = json.load(f)
            logger.info("SMS: TF-IDF model loaded (AUC=%.4f, trained on %d samples)",
                        meta.get("auc", 0), meta.get("n_train", 0))
        else:
            logger.info("SMS: TF-IDF model loaded from %s", TFIDF_DIR)

    @classmethod
    def get(cls) -> Optional["_TfidfModel"]:
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
                            "SMS classifier: TF-IDF model unavailable (%s). "
                            "Falling back to rule engine.", e)
        return cls._instance

    def predict_proba(self, message: str) -> float:
        """Returns P(spam/phishing) in [0, 1]."""
        X = self.vectorizer.transform([message])
        return float(self.clf.predict_proba(X)[0, 1])


# ===========================================================================
# Status / diagnostics
# ===========================================================================
def model_status() -> dict:
    if MODEL_BACKEND == "rules":
        return {"backend": "rules", "reason": "forced by MODEL_BACKEND=rules"}
    if MODEL_BACKEND == "tfidf":
        m = _TfidfModel.get()
        if m:
            return {"backend": "tfidf", "model_dir": TFIDF_DIR}
        return {"backend": "rules", "reason": f"TF-IDF model missing in {TFIDF_DIR}"}
    if MODEL_BACKEND == "transformer":
        m = _TransformerModel.get()
        if m:
            return {"backend": "transformer", "model_dir": TRANSFORMER_DIR,
                    "device": m.device}
        raise RuntimeError(
            f"MODEL_BACKEND=transformer but model not found at {TRANSFORMER_DIR}")
    # auto: transformer → tfidf → rules
    m_t = _TransformerModel.get()
    if m_t:
        return {"backend": "transformer", "model_dir": TRANSFORMER_DIR,
                "device": m_t.device}
    m_f = _TfidfModel.get()
    if m_f:
        return {"backend": "tfidf", "model_dir": TFIDF_DIR}
    return {"backend": "rules",
            "reason": f"transformer unavailable at {TRANSFORMER_DIR}; "
                      f"TF-IDF unavailable at {TFIDF_DIR}"}


# ===========================================================================
# Public API
# ===========================================================================
def classify_sms(message: str) -> SMSClassificationResult:
    keywords_found = _find_keywords(message)
    has_url        = _has_suspicious_url(message)
    has_phone      = _has_embedded_phone(message)
    impersonates   = _mentions_bank_brand(message)

    score    = None
    backend  = "rules"

    if MODEL_BACKEND not in ("rules",):
        # Tier 1: transformer
        if MODEL_BACKEND in ("auto", "transformer"):
            t = _TransformerModel.get()
            if t is not None:
                try:
                    score   = t.predict_proba(message) * 100.0
                    backend = "transformer"
                except Exception as e:
                    logger.error("Transformer inference failed (%s); trying TF-IDF", e)

        # Tier 2: TF-IDF ML model
        if score is None and MODEL_BACKEND in ("auto", "tfidf"):
            f = _TfidfModel.get()
            if f is not None:
                try:
                    score   = f.predict_proba(message) * 100.0
                    backend = "tfidf"
                except Exception as e:
                    logger.error("TF-IDF inference failed (%s); using rules", e)

    if score is None:
        if MODEL_BACKEND == "transformer":
            raise RuntimeError(
                f"Transformer required but unavailable ({TRANSFORMER_DIR})")
        score   = _rule_score(keywords_found, has_url, impersonates, has_phone)
        backend = "rules"

    if score >= FRAUD_THRESHOLD:
        classification = "fraud"
    elif score >= SUSPICIOUS_THRESHOLD:
        classification = "suspicious"
    else:
        classification = "safe"

    return SMSClassificationResult(
        classification=classification,
        risk_score=round(score, 1),
        explanation=_build_explanation(
            classification, keywords_found, has_url,
            impersonates, score, backend),
        suspicious_keywords=keywords_found,
        contains_suspicious_url=has_url,
    )
