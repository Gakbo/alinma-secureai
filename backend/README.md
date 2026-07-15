# Alinma SecureAI — Backend

Intelligent Fraud & Scam Prevention Platform for Alinma Bank (AMAD Hackathon MVP).

FastAPI backend covering: SMS phishing detection, transaction risk scoring,
fraud alerts, customer security score, and the analyst dashboard, matching
the project spec's functional requirements (FR1–FR7).

## 1. Setup

```bash
cd alinma-secureai-backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

By default this uses **SQLite** (`alinma_secureai.db`, created automatically) —
no database installation needed to run the demo.

To switch to PostgreSQL later:
1. Install PostgreSQL and create a database.
2. Copy `.env.example` to `.env` and set `DATABASE_URL`.
3. Install `python-dotenv` if you want auto-loading, or just `export` the
   variable manually before running uvicorn.

## 2. Seed demo data (recommended before your presentation)

```bash
python seed_data.py
```

This creates two customer accounts and one analyst account, plus one
sample high-risk alert. Printed credentials, e.g.:

```
customer   -> email: sara.customer@example.com       password: Password123
customer   -> email: fahad.customer@example.com      password: Password123
analyst    -> email: analyst@alinma.com               password: Password123
```

## 3. Run the server

```bash
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000/docs** — interactive Swagger UI where you can
try every endpoint directly (great for demoing to judges without a frontend).

## 4. API Overview

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/auth/register` | POST | none | Create a user (customer/analyst/admin) |
| `/auth/login` | POST | none | Login (form: `username`=email, `password`) → JWT |
| `/auth/me` | GET | any | Current user profile / security score |
| `/sms/check` | POST | any | FR2 — SMS phishing detection |
| `/transactions/check` | POST | any | FR3 — transaction risk analysis |
| `/alerts/` | GET | any | FR4 — alert history (own alerts for customers, all for analysts) |
| `/alerts/{id}` | PATCH | analyst/admin | Resolve/reopen an alert |
| `/dashboard/summary` | GET | analyst/admin | FR6 — fraud stats overview |
| `/dashboard/high-risk-users` | GET | analyst/admin | FR6 — high-risk customer list |
| `/dashboard/recent-alerts` | GET | analyst/admin | FR6 — recent fraud alerts |

## 5. Demo flow (matches your pitch script)

1. **Register/login** as `sara.customer@example.com` → copy the `access_token`
   from the login response, click "Authorize" in `/docs` and paste it in as
   `Bearer <token>`.
2. **Scene 1 — Phishing SMS**: POST to `/sms/check` with:
   ```json
   { "message": "Dear Alinma customer, your account will be blocked. Click here immediately: http://alinma-verify.xyz" }
   ```
   Returns `fraud`, a risk score, and a plain-language explanation.
3. **Scene 2 — Transaction check**: POST to `/transactions/check` with:
   ```json
   { "amount": 20000, "recipient": "New Beneficiary LLC", "is_new_recipient": true, "country": "PK" }
   ```
   Returns `high` risk, `verify`/`reject` action, and an explanation.
4. **Scene 3 — Explanation**: already included in both responses above
   (`explanation` field) — read it aloud as the "AI Explanation Engine".
5. **Scene 4 — Dashboard**: login as `analyst@alinma.com`, then call
   `/dashboard/summary` and `/dashboard/recent-alerts`.

## 6. Where the real ML models plug in later

Every AI function lives in `app/ml/` with a rule-based MVP implementation
and a comment explaining exactly how to swap in the trained model from the
spec, without touching any router code:

- `ml/sms_classifier.py` → replace with fine-tuned multilingual BERT
- `ml/transaction_risk.py` → replace with trained XGBoost / Random Forest
- `ml/behavior_anomaly.py` → replace with trained Isolation Forest

This is intentional: it lets you demo a fully working, explainable system
now, and swap in real trained models incrementally as you build them —
without any of the routers, database, or frontend needing to change.

## 7. Security notes (NFR2)

- Passwords hashed with bcrypt (`passlib`)
- JWT-based auth (`python-jose`), role-based access via `require_role()`
- Run behind HTTPS/TLS in any real deployment
- SQLAlchemy ORM (parameterized queries) protects against SQL injection
- Set a strong, unique `SECRET_KEY` via environment variable in production
