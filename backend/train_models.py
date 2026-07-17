"""
Alinma SecureAI – Model Training Script
========================================
Trains two models from the uploaded CSV datasets and writes the artifacts
to backend/saved_models/ so the live API picks them up automatically.

Models trained:
  A. SMS TF-IDF + Logistic Regression (sms_ml backend)
     Combines: arabic_sms_spam, sms_spam_collection, arabic_english_sms_samples
     Saves:  saved_models/sms_ml/vectorizer.joblib
             saved_models/sms_ml/classifier.joblib
             saved_models/sms_ml/meta.json

  B. Transaction Fraud XGBoost (transaction risk)
     Source: synthetic_transactions
     Saves:  saved_models/fraud_xgboost_model.joblib
             saved_models/fraud_feature_encoder.joblib

Datasets live in backend/data/ (checked into the repo).

Run from repo root:
    python backend/train_models.py
"""

import os
import sys
import json
import logging
import pathlib

import numpy as np
import pandas as pd
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OrdinalEncoder, LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, roc_auc_score
import xgboost as xgb

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("train")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BACKEND_DIR = pathlib.Path(__file__).parent
DATA_DIR    = BACKEND_DIR / "data"
SAVE_DIR    = BACKEND_DIR / "saved_models"

TXN_CSV          = DATA_DIR / "synthetic_transactions.csv"
AR_EN_SMS_CSV    = DATA_DIR / "arabic_english_sms_samples.csv"
SMS_COLL_CSV     = DATA_DIR / "sms_spam_collection.csv"
AR_SPAM_CSV      = DATA_DIR / "arabic_sms_spam.csv"

SMS_SAVE_DIR     = SAVE_DIR / "sms_ml"
SMS_VEC_FILE     = SMS_SAVE_DIR / "vectorizer.joblib"
SMS_CLF_FILE     = SMS_SAVE_DIR / "classifier.joblib"
SMS_META_FILE    = SMS_SAVE_DIR / "meta.json"

TXN_MODEL_FILE   = SAVE_DIR / "fraud_xgboost_model.joblib"
TXN_ENC_FILE     = SAVE_DIR / "fraud_feature_encoder.joblib"

SAVE_DIR.mkdir(parents=True, exist_ok=True)
SMS_SAVE_DIR.mkdir(parents=True, exist_ok=True)

CATEGORICAL_COLS = ["country", "device_type"]
NUMERIC_COLS     = ["amount", "is_new_recipient", "device_trust_score",
                    "transaction_hour", "prior_transaction_count"]


# ===========================================================================
# MODEL A — SMS Classifier
# ===========================================================================

def load_sms_data() -> pd.DataFrame:
    """
    Combine the three SMS datasets into a single DataFrame with columns
    [text, label] where label ∈ {0=ham, 1=spam}.
    """
    frames = []

    # 1. Arabic-English Alinma samples  (message, label: phishing/safe)
    df1 = pd.read_csv(AR_EN_SMS_CSV)
    df1 = df1.rename(columns={"message": "text"})
    df1["label"] = df1["label"].str.strip().map({"phishing": 1, "safe": 0})
    df1 = df1[["text", "label"]].dropna()
    frames.append(df1)
    log.info("Arabic-English SMS: %d rows (%d spam, %d ham)",
             len(df1), df1["label"].sum(), (df1["label"] == 0).sum())

    # 2. UCI SMS Spam Collection  (v1: ham/spam, v2: message)
    df2 = pd.read_csv(SMS_COLL_CSV, usecols=[0, 1], header=0,
                      names=["label_str", "text"], encoding="latin-1")
    df2["label"] = df2["label_str"].str.strip().map({"spam": 1, "ham": 0})
    df2 = df2[["text", "label"]].dropna()
    frames.append(df2)
    log.info("SMS Spam Collection: %d rows (%d spam, %d ham)",
             len(df2), df2["label"].sum(), (df2["label"] == 0).sum())

    # 3. Arabic SMS Spam  (SMS, Sentiment: 1=spam, 0=ham)
    df3 = pd.read_csv(AR_SPAM_CSV, encoding="utf-8-sig")
    # Some files have BOM; strip it from column names
    df3.columns = df3.columns.str.strip().str.lstrip("\ufeff")
    df3 = df3.rename(columns={"SMS": "text", "Sentiment": "label"})
    df3["label"] = pd.to_numeric(df3["label"], errors="coerce")
    df3 = df3[["text", "label"]].dropna()
    df3["label"] = df3["label"].astype(int)
    frames.append(df3)
    log.info("Arabic SMS Spam: %d rows (%d spam, %d ham)",
             len(df3), df3["label"].sum(), (df3["label"] == 0).sum())

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.dropna(subset=["text", "label"])
    combined["text"] = combined["text"].astype(str).str.strip()
    combined = combined[combined["text"].str.len() > 0]
    log.info("Combined SMS dataset: %d rows total (%d spam, %d ham)",
             len(combined), combined["label"].sum(),
             (combined["label"] == 0).sum())
    return combined


def train_sms_model(df: pd.DataFrame) -> dict:
    """
    TF-IDF (char + word n-grams, language-agnostic) → Logistic Regression.
    Char n-grams handle Arabic morphology and misspellings naturally.
    """
    X = df["text"].values
    y = df["label"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42, stratify=y)

    log.info("Training SMS TF-IDF vectorizer ...")
    vectorizer = TfidfVectorizer(
        analyzer="char_wb",     # character n-grams inside word boundaries
        ngram_range=(2, 5),     # bigrams → 5-grams
        max_features=80_000,
        sublinear_tf=True,      # log(1+tf) — tames high-frequency terms
        min_df=2,
        strip_accents=None,     # keep Arabic diacritics
    )
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec  = vectorizer.transform(X_test)

    log.info("Training Logistic Regression classifier ...")
    clf = LogisticRegression(
        C=5.0,
        max_iter=1000,
        class_weight="balanced",  # handles any class imbalance
        solver="lbfgs",
        n_jobs=-1,
    )
    clf.fit(X_train_vec, y_train)

    y_pred  = clf.predict(X_test_vec)
    y_proba = clf.predict_proba(X_test_vec)[:, 1]
    auc     = roc_auc_score(y_test, y_proba)

    report = classification_report(y_test, y_pred, target_names=["ham", "spam"])
    log.info("SMS classifier — test set:\n%s", report)
    log.info("SMS classifier — ROC-AUC: %.4f", auc)

    joblib.dump(vectorizer, SMS_VEC_FILE)
    joblib.dump(clf, SMS_CLF_FILE)

    meta = {
        "auc": round(auc, 4),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "features": int(vectorizer.max_features),
        "sources": ["arabic_english_sms_samples", "sms_spam_collection", "arabic_sms_spam"],
    }
    with open(SMS_META_FILE, "w") as f:
        json.dump(meta, f, indent=2)

    log.info("Saved SMS model artifacts to %s", SMS_SAVE_DIR)
    return meta


# ===========================================================================
# MODEL B — Transaction Fraud XGBoost
# ===========================================================================

def load_transaction_data() -> pd.DataFrame:
    df = pd.read_csv(TXN_CSV)
    log.info("Transactions: %d rows, %d fraud (%.1f%%)",
             len(df), df["is_fraud"].sum(),
             100 * df["is_fraud"].mean())
    return df


def train_transaction_model(df: pd.DataFrame) -> dict:
    """
    XGBoost binary classifier on tabular transaction features.
    Categorical columns are ordinal-encoded (matches the inference path in
    transaction_risk.py which also uses OrdinalEncoder).
    """
    feature_cols = NUMERIC_COLS + CATEGORICAL_COLS
    X = df[feature_cols].copy()
    y = df["is_fraud"].values

    # Encode categoricals
    encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    X[CATEGORICAL_COLS] = encoder.fit_transform(X[CATEGORICAL_COLS])

    X_train, X_test, y_train, y_test = train_test_split(
        X.values, y, test_size=0.15, random_state=42, stratify=y)

    scale_pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    log.info("Training XGBoost (scale_pos_weight=%.2f) ...", scale_pos_weight)

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    y_pred  = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    auc     = roc_auc_score(y_test, y_proba)

    report = classification_report(y_test, y_pred, target_names=["legit", "fraud"])
    log.info("Transaction model — test set:\n%s", report)
    log.info("Transaction model — ROC-AUC: %.4f", auc)

    # Feature importances
    importances = dict(zip(feature_cols, model.feature_importances_))
    top = sorted(importances.items(), key=lambda x: -x[1])[:5]
    log.info("Top-5 features: %s", top)

    joblib.dump(model, TXN_MODEL_FILE)
    joblib.dump(encoder, TXN_ENC_FILE)
    log.info("Saved transaction model artifacts to %s", SAVE_DIR)

    meta = {
        "auc": round(auc, 4),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "top_features": top,
        "source": "synthetic_transactions",
    }
    with open(SAVE_DIR / "fraud_model_meta.json", "w") as f:
        json.dump(meta, f, indent=2, default=str)

    return meta


# ===========================================================================
# Main
# ===========================================================================

def main():
    log.info("=" * 60)
    log.info("Alinma SecureAI — Model Training")
    log.info("=" * 60)

    # --- SMS ---
    log.info("\n[1/2] Training SMS Classifier (TF-IDF + Logistic Regression)")
    sms_df  = load_sms_data()
    sms_meta = train_sms_model(sms_df)

    # --- Transactions ---
    log.info("\n[2/2] Training Transaction Fraud Model (XGBoost)")
    txn_df   = load_transaction_data()
    txn_meta = train_transaction_model(txn_df)

    log.info("\n%s", "=" * 60)
    log.info("Training complete.")
    log.info("  SMS model AUC  : %.4f", sms_meta["auc"])
    log.info("  TXN model AUC  : %.4f", txn_meta["auc"])
    log.info("Artifacts written to %s", SAVE_DIR)
    log.info("Restart the backend API to activate the new models.")


if __name__ == "__main__":
    main()
