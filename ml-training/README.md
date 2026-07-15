# Alinma SecureAI — Model Training

Training scripts for the three AI models in your tech stack, using the
datasets we verified earlier (SMS Spam Collection, IEEE-CIS/Credit Card
Fraud) plus synthetic data generators so you can run everything today
without waiting on Kaggle downloads.

## 1. Setup

```bash
cd alinma-model-training
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

`transformers`/`torch` are only needed if you run `train_bert_finetune.py`.
If you're only doing the TF-IDF baseline + fraud/anomaly models, you can
skip those two lines in requirements.txt to save install time.

## 2. Generate data (works immediately, no downloads needed)

```bash
python data/generate_synthetic_transactions.py     # -> data/synthetic_transactions.csv
python data/generate_arabic_sms_samples.py          # -> data/arabic_english_sms_samples.csv
```

## 3. (Optional but recommended) Add the real English SMS dataset

Download **SMS Spam Collection** from
https://www.kaggle.com/datasets/uciml/sms-spam-collection-dataset,
save as `data/sms_spam_collection.csv`. The training script auto-detects
and renames its `v1`/`v2` columns.

Without this file, the SMS model still trains — just on the smaller
synthetic Arabic/English set alone, which is weaker.

## 4. Train the models

```bash
# Model A (MVP): SMS phishing classifier, TF-IDF + Logistic Regression
python sms_model/train_tfidf_baseline.py

# Model A (full, needs GPU/Colab for reasonable speed): AraBERT/mBERT fine-tune
python sms_model/train_bert_finetune.py --model_name aubmindlab/bert-base-arabertv2

# Model B: Transaction fraud detection, XGBoost + Random Forest
python fraud_model/train_fraud_model.py --data data/synthetic_transactions.csv

# Model C: Behavior anomaly detection, Isolation Forest
python fraud_model/train_anomaly_model.py
```

Each script prints accuracy, precision, recall, F1, ROC-AUC, and (for the
fraud model) PR-AUC — the metric that matters most given the class
imbalance you already flagged in your challenges slide.

## 5. What gets saved

```
saved_models/
├── sms_tfidf_vectorizer.joblib
├── sms_logreg_model.joblib
├── bert_sms_classifier/            (only if you ran train_bert_finetune.py)
├── fraud_xgboost_model.joblib
├── fraud_random_forest_model.joblib
├── fraud_feature_encoder.joblib
├── anomaly_isolation_forest.joblib
└── anomaly_feature_encoder.joblib
```

## 6. Plugging trained models into the FastAPI backend

The backend's `app/ml/` modules were written specifically so this swap is
a small, contained change — no router or database code needs to touch.

### `app/ml/sms_classifier.py`

Replace the rule-based body of `classify_sms()` with:

```python
import joblib

_vectorizer = joblib.load("saved_models/sms_tfidf_vectorizer.joblib")
_model = joblib.load("saved_models/sms_logreg_model.joblib")

def classify_sms(message: str) -> SMSClassificationResult:
    vec = _vectorizer.transform([message.lower().strip()])
    proba = _model.predict_proba(vec)[0][1]  # probability of "phishing"
    score = round(proba * 100, 1)

    if score >= 70:
        classification = "fraud"
    elif score >= 35:
        classification = "suspicious"
    else:
        classification = "safe"

    # Keep using the existing keyword/URL helpers for the explanation --
    # a trained model's score alone isn't explainable to a customer.
    keywords_found = _find_keywords(message)
    has_url = _has_suspicious_url(message)
    explanation = build_explanation(
        [f"model flagged this with {score:.0f}% phishing probability"]
        + (["contains urgency/scam phrasing"] if keywords_found else [])
        + (["contains a suspicious link"] if has_url else [])
    ) if classification != "safe" else "No suspicious patterns found in this message."

    return SMSClassificationResult(classification, score, explanation, keywords_found, has_url)
```

This keeps the same keyword/URL detection for the *explanation* (since
"91% phishing probability" alone isn't useful to a customer), while using
the real trained model for the actual score -- combining accuracy with
explainability, which is exactly what your AI Explanation Engine (FR7)
is meant to do.

### `app/ml/transaction_risk.py`

Replace the rule-based body of `score_transaction()` similarly: load
`fraud_xgboost_model.joblib` + `fraud_feature_encoder.joblib`, build the
same feature vector shape used in training (`amount`, `is_new_recipient`,
`device_trust_score`, `transaction_hour`, `prior_transaction_count`, one-hot
`country`/`device_type`), call `model.predict_proba(...)`, and keep the
existing `reasons` logic for the explanation text.

### `app/ml/behavior_anomaly.py`

Load `anomaly_isolation_forest.joblib` and call `model.predict(X)` /
`model.decision_function(X)` instead of the z-score fallback.

## 7. Known gap to mention in Q&A

IEEE-CIS and Credit Card Fraud datasets model **card-not-present /
credit-card transactions**, not bank transfers -- that's why the fraud
model here trains on the synthetic transaction generator by default,
which mimics wire-transfer-style features (new beneficiary, country,
device trust) instead. If asked, this is the honest answer: public
datasets informed the feature engineering and imbalance-handling approach,
but the actual training data is synthetic because no public dataset
matches Alinma's real transaction structure -- and real Alinma data is
private.
