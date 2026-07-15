# Alinma SecureAI

**AI-Powered Fraud Prevention Platform for Alinma Bank** — AMAD Fintech Hackathon

> Alinma SecureAI proactively protects Alinma Bank customers by detecting
> phishing messages, assessing transaction risks in real time, and identifying
> suspicious customer behavior **before financial loss occurs**, through
> Machine Learning, Natural Language Processing, and Behavioral Analytics.

Prevention, not detection: existing systems react after money is lost;
SecureAI scores the SMS before the customer clicks and the transfer before
the money moves.

## The three AI models

| Model | Task | Algorithm | Where |
|---|---|---|---|
| A | Phishing SMS detection (Arabic + English) | AraBERT / mBERT (TF-IDF + LogReg for MVP) | `ml-training/sms_model/` |
| B | Transaction fraud risk | XGBoost / Random Forest | `ml-training/fraud_model/train_fraud_model.py` |
| C | Behavior anomaly detection | Isolation Forest | `ml-training/fraud_model/train_anomaly_model.py` |

All three plug into `backend/app/ml/`, which currently ships with transparent
rule-based versions so the platform demos end-to-end **today**; each file
documents its exact swap-in path for the trained model (see
`ml-training/README.md` §6).

## Repository layout

```
AlinmaSecureAI/
├── backend/        FastAPI + SQLAlchemy + JWT  (SMS check, transaction risk,
│                   alerts, security score, analyst dashboard APIs)
├── frontend/       React + Tailwind + Axios + Chart.js  (Login, SMS Scanner,
│                   Transfer Guardian, Fraud Alerts, Analyst Dashboard)
├── ml-training/    Dataset generators + training scripts for Models A/B/C
├── docker-compose.yml   One-command run: PostgreSQL + backend + frontend
└── .gitignore
```

## Quick start (development)

Terminal 1 — backend:
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python seed_data.py          # demo accounts + sample alert
uvicorn app.main:app --reload
```

Terminal 2 — frontend:
```bash
cd frontend
npm install
npm run dev                  # http://localhost:5173 (proxies /api -> :8000)
```

Demo accounts (from `seed_data.py`):
| Role | Email | Password |
|---|---|---|
| customer | sara.customer@example.com | Password123 |
| customer | fahad.customer@example.com | Password123 |
| analyst | analyst@alinma.com | Password123 |

## Quick start (Docker, closest to production)

```bash
docker compose up --build
# frontend  -> http://localhost:3000
# backend   -> http://localhost:8000/docs
# database  -> PostgreSQL 16 (persisted volume)
docker compose exec backend python seed_data.py   # once, to create demo accounts
```

## The 3-minute demo script

1. **Scene 1 — Phishing SMS** · Sign in as Sara → SMS Scanner → "Use demo
   phishing sample" → Analyze. The AI returns a fraud verdict with a risk
   score and a plain-language explanation, and an alert is generated.
2. **Scene 2 — High-risk transfer** · Transfer Guardian → "Use demo high-risk
   transfer" (SAR 20,000, new beneficiary, foreign destination) → Score.
   Verdict: high risk, verification required, with reasons.
3. **Scene 3 — Explanation** · Both verdict panels show *why*: new recipient,
   amount above normal behavior, suspicious link — FR7's Explanation Engine.
4. **Scene 4 — Analyst view** · Sign out, sign in as the analyst → Dashboard:
   live stats, alerts by severity (doughnut), attack types (bar),
   high-risk customer table — all rendered with Chart.js from live API data.

Closing line: *"Alinma SecureAI transforms banking security from reactive
detection to proactive prevention."*

## Training the real models

See `ml-training/README.md`. Short version:

```bash
cd ml-training
pip install -r requirements.txt
python data/generate_synthetic_transactions.py
python data/generate_arabic_sms_samples.py
python sms_model/train_tfidf_baseline.py          # Model A (MVP)
python fraud_model/train_fraud_model.py           # Model B
python fraud_model/train_anomaly_model.py         # Model C
```

Verified real outputs from these pipelines (honest numbers for the
Testing & Verification section — do not quote accuracy figures you have
not measured):
- SMS baseline correctly classified Arabic + English phishing samples
  (e.g. 78.9% phishing probability on the Alinma impersonation demo SMS)
  and cleared legitimate OTP messages.
- Synthetic transaction generator produces a 3.50% fraud rate, matching
  the real-world IEEE-CIS benchmark ratio.
- Isolation Forest flagged 5.00% of transactions as anomalous with 55.8%
  overlap with the true fraud label — unsupervised, no labels seen.

Public benchmark datasets referenced: SMS Spam Collection (UCI/Kaggle,
5,574 messages), IEEE-CIS Fraud Detection (~590K transactions, ~3.5% fraud),
Credit Card Fraud Detection (ULB: 284,807 transactions, 492 fraud, 0.172%).

## Git setup

```bash
cd AlinmaSecureAI
git init
git add .
git commit -m "Alinma SecureAI: fraud prevention platform MVP"
git branch -M main
git remote add origin https://github.com/<your-team>/alinma-secureai.git
git push -u origin main
```

Suggested branch model for the team: `main` (stable demo) ← `dev` ←
`feature/<name>` per task.

## Security (NFR2)

bcrypt password hashing · JWT auth with role-based access
(customer/analyst/admin) · SQLAlchemy ORM (parameterized queries → SQL
injection protection) · CORS configured · HTTPS/TLS assumed at deployment ·
secrets via environment variables.

## Team

Fraud Hawks — عبدالله العامري · معاذ نافيد · محمد آل سعيد
