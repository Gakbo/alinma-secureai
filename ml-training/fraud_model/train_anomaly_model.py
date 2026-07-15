"""
Model C: Behavior Anomaly Detection using Isolation Forest -- unsupervised,
so it doesn't need fraud labels; it learns what "normal" customer behavior
looks like and flags outliers (unusual login times, sudden high amounts,
new devices), matching your tech stack doc.

Data expected:
    data/synthetic_transactions.csv (same file as train_fraud_model.py --
    Isolation Forest ignores the is_fraud column and learns from the
    behavioral features alone)

Run:
    python train_anomaly_model.py

Output:
    saved_models/anomaly_isolation_forest.joblib
    saved_models/anomaly_feature_encoder.joblib
"""
import os
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import OneHotEncoder
import joblib

DATA_PATH = "data/synthetic_transactions.csv"
MODEL_DIR = "saved_models"

CATEGORICAL_COLS = ["country", "device_type"]
NUMERIC_COLS = ["amount", "is_new_recipient", "device_trust_score",
                "transaction_hour", "prior_transaction_count"]


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)

    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"{DATA_PATH} not found. Run generate_synthetic_transactions.py first.")

    df = pd.read_csv(DATA_PATH)

    encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    cat_encoded = encoder.fit_transform(df[CATEGORICAL_COLS])
    cat_df = pd.DataFrame(cat_encoded, columns=encoder.get_feature_names_out(CATEGORICAL_COLS))
    X = pd.concat([df[NUMERIC_COLS].reset_index(drop=True), cat_df.reset_index(drop=True)], axis=1)

    # contamination = expected proportion of anomalies; align with roughly
    # what fraction of behavior we'd expect to be genuinely unusual.
    model = IsolationForest(
        n_estimators=200,
        contamination=0.05,
        random_state=42,
    )
    model.fit(X)

    # -1 = anomaly, 1 = normal (sklearn's convention)
    preds = model.predict(X)
    scores = model.decision_function(X)  # higher = more normal

    df_out = df.copy()
    df_out["anomaly_flag"] = (preds == -1).astype(int)
    df_out["anomaly_score"] = scores

    print(f"Flagged {df_out['anomaly_flag'].sum()} anomalies out of {len(df_out)} "
          f"({df_out['anomaly_flag'].mean():.2%})")

    # Sanity check: anomaly flag should correlate with the fraud label, even
    # though the model never saw it during training.
    if "is_fraud" in df_out.columns:
        overlap = df_out[df_out["anomaly_flag"] == 1]["is_fraud"].mean()
        print(f"Of flagged anomalies, {overlap:.2%} were also labeled fraud "
              f"(sanity check -- not a formal evaluation, since this model is unsupervised).")

    joblib.dump(model, os.path.join(MODEL_DIR, "anomaly_isolation_forest.joblib"))
    joblib.dump(encoder, os.path.join(MODEL_DIR, "anomaly_feature_encoder.joblib"))
    print(f"\nSaved model + encoder to {MODEL_DIR}/")


if __name__ == "__main__":
    main()
