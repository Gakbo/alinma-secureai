"""
Generates a synthetic banking transaction dataset that mimics the structure
of real fraud datasets (IEEE-CIS / Credit Card Fraud) but simulates Alinma
Bank-style transactions, since real customer data is private (per your
"Data Sources" slide: "synthetic banking transaction data ... respecting
customer privacy and banking regulations").

Run:
    python generate_synthetic_transactions.py

Output:
    data/synthetic_transactions.csv
"""
import numpy as np
import pandas as pd

np.random.seed(42)

N_ROWS = 20000
FRAUD_RATE = 0.035  # matches IEEE-CIS's real-world ~3.5% fraud rate

COUNTRIES = ["SA", "AE", "PK", "IN", "EG", "UK", "US", "NG"]
COUNTRY_WEIGHTS = [0.70, 0.08, 0.06, 0.05, 0.04, 0.03, 0.02, 0.02]
DEVICE_TYPES = ["mobile", "web", "atm"]


def generate_row(is_fraud: bool) -> dict:
    if is_fraud:
        amount = np.round(np.random.lognormal(mean=8.5, sigma=1.2), 2)  # skewed toward larger amounts
        is_new_recipient = np.random.choice([0, 1], p=[0.25, 0.75])
        country = np.random.choice(COUNTRIES, p=COUNTRY_WEIGHTS) if np.random.rand() > 0.5 else \
            np.random.choice(["PK", "NG", "UK", "US"])
        device_trust_score = np.round(np.random.uniform(0, 60), 1)
        hour = np.random.choice(list(range(0, 6)) + list(range(22, 24)))  # unusual hours
        prior_txn_count = np.random.randint(0, 10)
    else:
        amount = np.round(np.random.lognormal(mean=6.5, sigma=0.9), 2)
        is_new_recipient = np.random.choice([0, 1], p=[0.85, 0.15])
        country = np.random.choice(COUNTRIES, p=COUNTRY_WEIGHTS)
        device_trust_score = np.round(np.random.uniform(60, 100), 1)
        hour = np.random.randint(6, 22)
        prior_txn_count = np.random.randint(5, 200)

    return {
        "amount": amount,
        "is_new_recipient": is_new_recipient,
        "country": country,
        "device_type": np.random.choice(DEVICE_TYPES),
        "device_trust_score": device_trust_score,
        "transaction_hour": hour,
        "prior_transaction_count": prior_txn_count,
        "is_fraud": int(is_fraud),
    }


def main():
    n_fraud = int(N_ROWS * FRAUD_RATE)
    n_legit = N_ROWS - n_fraud

    rows = [generate_row(is_fraud=False) for _ in range(n_legit)]
    rows += [generate_row(is_fraud=True) for _ in range(n_fraud)]

    df = pd.DataFrame(rows).sample(frac=1, random_state=42).reset_index(drop=True)
    df.to_csv("data/synthetic_transactions.csv", index=False)

    print(f"Generated {len(df)} synthetic transactions "
          f"({df['is_fraud'].sum()} fraud, {(1 - df['is_fraud']).sum()} legitimate)")
    print(f"Fraud rate: {df['is_fraud'].mean():.2%}")
    print("Saved to data/synthetic_transactions.csv")


if __name__ == "__main__":
    main()
