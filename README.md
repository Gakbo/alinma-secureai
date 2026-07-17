# Alinma SecureAI

**AI-Powered Fraud Prevention Platform for Alinma Bank** — AMAD Fintech Hackathon 2026

> Alinma SecureAI proactively protects Alinma Bank customers by detecting
> phishing messages, assessing transaction risk in real time, and identifying
> suspicious behaviour **before financial loss occurs** — using Machine
> Learning, Natural Language Processing, and Behavioural Analytics.

**Prevention, not detection.** Existing systems react after the money is gone.
SecureAI scores the SMS *before* the customer clicks, and the transfer *before*
the money moves.

---

## Results

Model A (phishing SMS) is a **fine-tuned XLM-RoBERTa**, trained on **6,043 real
and synthetic messages** from three sources. Measured on a held-out 20% split:

| Slice | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|---|
| **Overall** | 0.9901 | 0.9734 | 0.9632 | **0.9683** | 0.9981 |
| **Arabic** | — | 1.0000 | 0.9697 | **0.9846** | — |

On the Arabic slice — real Saudi bank phishing, the actual threat we target —
the model produced **zero false alarms and missed one scam out of 33**.

We report per-language metrics deliberately. The English corpus is ~11× larger
than the Arabic one, so a single headline number would be dominated by English
generic spam and would say almost nothing about Arabic bank phishing. See
[Honest limitations](#honest-limitations).

Model selection was empirical: `benchmark_models.py` trained XLM-R, mBERT and
AraBERT under identical conditions. All three landed **within noise of each
other** (~1 message difference on 1,209). XLM-R was chosen on tie-breakers that
matter operationally — best-equal Arabic F1, no checkpoint-reload warnings, and
the broadest multilingual pretraining for code-switched Arabic/English.

---

## Capabilities

| # | Feature | Status |
|---|---|---|
| 1 | **SMS Scanner** — paste an Arabic/English SMS, get a risk score + plain-language reason | ✅ 3-tier: XLM-RoBERTa → TF-IDF ML → rules |
| 2 | **Transfer Guardian** — score a transfer before it sends | ✅ XGBoost + explainable rule layer ([caveats](#honest-limitations)) |
| 3 | **Fraud Alerts** — high-risk events auto-generate alerts; filters, analyst resolve, customer acknowledge | ✅ persisted |
| 4 | **Customer Security Score** — behaviour, device trust, scam exposure with animated rings, grade & recommendations | ✅ |
| 5 | **Analyst Dashboard** — live stats, 7-day fraud trend, severity/attack-type/region charts, high-risk customers, open-alert feed | ✅ Chart.js |
| 6 | **AI Banking Assistant** — floating chat widget; OpenAI-powered with a bilingual rule-based IVR fallback (7 topics) | ✅ works with or without an API key |
| 7 | **Customer signup** — self-registration with server-enforced customer role and `@alinma.com` staff-domain block | ✅ |
| 8 | **Forgot / reset password** — emailed single-use tokens, 1-hour expiry, rate limiting, old sessions invalidated | ✅ dev console fallback |
| 9 | **Admin Panel** — user list, inline role changes, server-side domain guard | ✅ admin-only |
| 10 | **Full English / Arabic UI** — every page, chart label, form and chatbot reply; RTL/LTR switches live | ✅ |

Every risk verdict ships with a **human-readable explanation** (FR7). The model
supplies the score; a transparent rule layer supplies the *reason*. A customer
cannot act on "0.87 fraud probability" — they can act on *"this impersonates
Alinma Bank and contains an unrecognised link."*

---

## Architecture

```
              React + Tailwind (Axios · EN/AR · RTL)
                              |
                         FastAPI + JWT
      ┌───────────┬───────────┼───────────┬───────────┐
      ▼           ▼           ▼           ▼           ▼
 SMS Scanner  Transfer   Dashboard    AI Chat     Admin /
              Guardian   + Alerts    Assistant     Auth
      |           |           |           |           |
 XLM-R/TF-IDF  XGBoost   Chart.js   OpenAI + IVR  bcrypt +
   + rules    + rules                  rules     pwd_version
      └───────────┴─► Explanation ◄┘
                              |
                    PostgreSQL / SQLite
                              |
                     SMTP (reset + alert emails,
                      console fallback in dev)
```

**Stack:** React · Tailwind · Axios · Chart.js · FastAPI · JWT · bcrypt ·
SQLAlchemy · PostgreSQL/SQLite · PyTorch · Transformers · scikit-learn ·
XGBoost · Docker

---

## Repository layout

```
AlinmaSecureAI/
├── backend/            FastAPI + SQLAlchemy + JWT
│   ├── app/ml/         Model serving: score (model) + reason (rules)
│   ├── app/routers/    auth · sms · transactions · alerts · dashboard · admin · chat
│   ├── app/email_utils.py  Password-reset + fraud-alert emails (console fallback)
│   ├── data/           Training CSVs for the quick-train script (committed)
│   ├── tests/          pytest suites: registration, password reset, email
│   ├── train_models.py Quick-train: TF-IDF SMS tier + XGBoost (minutes, no GPU)
│   └── saved_models/   Trained model artifacts (gitignored, ~1.1GB transformer)
├── frontend/           React + Tailwind + Axios + Chart.js
│   └── src/i18n.js     Full English/Arabic string catalogue (RTL-aware)
├── ml-training/        Config-driven training pipeline (transformer path)
│   ├── config/         training_config.yaml — switch models without code edits
│   ├── sms_model/      Registry, validation, imbalance, augmentation, benchmark
│   └── fraud_model/    XGBoost + Isolation Forest
├── docs/smtp-setup.md  Email provider walkthroughs (Gmail / Resend)
├── scripts/            copy_model.ps1 — deploy a trained model to the backend
└── docker-compose.yml  PostgreSQL + backend + frontend
```

---

## Quick start

**Requirements:** Python **3.12** (not 3.13/3.14 — the ML stack lags), Node 20+.

**Backend:**
```bash
cd backend
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1        # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cpu   # optional (transformer tier)
python seed_data.py                # WARNING: drops + recreates all tables with demo data
python train_models.py             # optional: trains TF-IDF SMS tier + XGBoost in ~1 min
uvicorn app.main:app --reload
```

Environment variables load from `backend/.env` automatically — copy
`backend/.env.example` and edit. Everything is optional in development:
without SMTP credentials, password-reset links print to the backend console;
without `OPENAI_API_KEY`, the chatbot answers from its bilingual rule engine.

**Frontend:**
```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173
```

Check **http://localhost:8000/** — it reports which SMS backend is live:
```json
{ "sms_model": { "backend": "transformer", "device": "cpu" } }
```
`"backend": "tfidf"` means the quick-trained ML tier is serving (good).
`"backend": "rules"` means no trained model is loaded — run
`python train_models.py`, or see
[Deploying a trained model](#deploying-a-trained-model) for the transformer.

**Demo accounts** (from `seed_data.py`):

| Role | Email | Password |
|---|---|---|
| customer | sara.customer@example.com (and fahad · mohammed · noura · khalid) | Password123 |
| analyst | analyst@alinma.com | Password123 |
| admin | admin@alinma.com | Password123 |

Staff accounts must use `@alinma.com` emails; public signup is customers-only
and the backend enforces both.

**Docker:**
```bash
docker compose up --build          # frontend :3000 · backend :8000 · PostgreSQL
docker compose exec backend python seed_data.py
```
Optional env vars (`OPENAI_API_KEY`, `SMTP_*`, `APP_URL`, `CORS_ORIGINS`) pass
through `docker-compose.yml` from your shell or a repo-root `.env` file.

**Tests:**
```bash
cd backend
python -m pytest tests/            # 42 tests: signup, password reset, JWT invalidation, email
```

---

## Demo script (4 minutes)

1. **Phishing SMS** — sign in as Sara → *SMS Scanner* → pick a demo sample →
   **Fraud, ~98/100**, with the reason spelled out. An alert is generated
   automatically (and a fraud-alert email in production).
2. **High-risk transfer** — *Transfer Guardian* → "High risk — large foreign
   transfer" scenario → **High risk — recommend blocking.**
3. **Ask the assistant** — open the floating chat bubble → type `2` → instant
   guidance on spotting fake SMS. Toggle عربي: the entire app flips to Arabic
   RTL, chatbot included.
4. **Security Score** — Sara's live risk profile: grade, three animated ring
   scores, targeted recommendations that react to the scans you just ran.
5. **Acknowledge the alert** — *Fraud Alerts* → Sara acknowledges; the badge
   survives refresh (persisted server-side).
6. **Analyst view** — sign in as the analyst → *Dashboard*: 7-day trend,
   severity/type/region charts, open-alert feed, high-risk customers.
7. **Admin** — sign in as admin → *Admin Panel* → change a role inline; the
   domain guard blocks invalid combinations server-side.
8. **Password reset** — "Forgot your password?" → the reset link prints to the
   backend console in dev → set a new password → old sessions are instantly
   invalid (`password_version`).

> *"Alinma SecureAI turns fraud management from reactive detection into
> proactive prevention."*

---

## ML training pipeline

Everything is driven by `ml-training/config/training_config.yaml` — switch
models, tune hyperparameters, or change strategy **without editing Python**.

```bash
cd ml-training
py -3.12 -m venv venv && .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cu128   # RTX 50-series needs cu128

python data/generate_arabic_sms_samples.py
python sms_model/benchmark_models.py     # compare candidate models
python sms_model/train_transformer.py    # train the selected model fully
```

**Pipeline features**

- **Pluggable dataset registry** (`sms_datasets.py`) — add a dataset by writing
  one config entry; no training-code changes. Each entry carries a confidence
  weight, priority, source, language and licence. Priority resolves duplicates
  across datasets; weight flows into per-sample loss.
- **Validation report** (`dataset_validation.py`) — runs before every training
  run: columns, encodings, nulls, empty messages, invalid labels, duplicates,
  label distribution, Arabic share. *It caught 31 silent duplicates on first
  run.*
- **Automatic imbalance handling** (`imbalance.py`) — measures the ratio, picks
  the mildest effective strategy. Our data: 5.35× → class weights
  (safe 0.593 / phishing 3.176).
- **Optional augmentation** (`augmentation.py`) — conservative, training-split
  only, minority-class only, URL-protected. Off by default.
- **Per-language evaluation** (`language_eval.py`) — Arabic/English/mixed
  reported separately.
- **Automatic benchmarking** (`benchmark_models.py`) — trains all candidates,
  compares quality *and* cost (train time, GPU memory, model size, latency),
  and flags when the winning margin is within noise.
- **Training**: early stopping, warmup + linear decay, AdamW, gradient
  accumulation, auto-fp16, best-F1 checkpoint selection.

### Data sources

| Dataset | Rows | Language | Weight |
|---|---|---|---|
| [SMS Spam Collection](https://www.kaggle.com/datasets/uciml/sms-spam-collection-dataset) (UCI/Kaggle) | 5,574 | English | 1.0 |
| [Arabic-SMS-Spam-Data](https://github.com/KhalidAlsantali/Arabic-SMS-Spam-Data) — K. Alsantali, *A Naïve Bayes Classifier for Arabic SMS Spam Messages* | 494 | Arabic | 1.0 |
| Synthetic Arabic/English (generated) | 422 | Mixed | 0.5 |

Real Alinma customer data is unavailable for privacy and regulatory reasons —
synthetic data carries a lower confidence weight accordingly.

### Deploying a trained model

```powershell
.\scripts\copy_model.ps1      # copies ml-training → backend/saved_models/
```
Re-run after **every** retrain, or the backend keeps serving the old model.
Model artifacts are gitignored (~1.1 GB).

---

## Honest limitations

We would rather state these than have them found:

- **The XGBoost transaction model was trained on synthetic data.** The full
  pipeline (features → model → score → explanation → alert) is live — the
  backend now feeds it the customer's real device-trust profile and stored
  transaction-history depth — but the training data was generated by our own
  rules, so its near-perfect AUC on that data is circular. Treat its scores as
  a demonstration of the pipeline, not of real-world accuracy; it retrains on
  real Alinma data with zero code changes (`python backend/train_models.py`).
  Set `TXN_MODEL_BACKEND=rules` to force the transparent rule engine instead.
- **The Arabic evaluation set is small** (~93 messages in the test split). The
  98.5% F1 is genuine but rests on a narrow sample. More Arabic data is our top
  priority.
- **No real code-switched data.** The "mixed" slice is our own synthetic
  templates, so we do not quote it.
- **English data is 2011 UK generic spam**, not bank phishing — it broadens
  coverage but does not represent Saudi banking threats.
- **Model C (Isolation Forest)** is trained but not wired into the backend.
- **Reset-request rate limiting is in-memory** (per-process, resets on
  restart). Fine for a single backend instance; use a shared store (Redis)
  before scaling horizontally.
- **The chatbot's OpenAI tier needs an `OPENAI_API_KEY`.** Without one it
  falls back to the rule-based IVR menu — deterministic, bilingual, and free,
  but limited to its seven scripted topics.

---

## Security

- **bcrypt** password hashing · **JWT** auth with role-based access
  (customer/analyst/admin) · SQLAlchemy ORM (parameterised queries → SQL
  injection protection) · secrets via environment variables (`.env`,
  gitignored) · HTTPS/TLS assumed at deployment.
- **Signup hardening** — public registration always creates a `customer`
  account (a `role` field in the request body is ignored), and `@alinma.com`
  addresses are rejected server-side. Staff accounts are IT-managed.
- **Domain guard** — analyst/admin roles require an `@alinma.com` email; the
  backend enforces this at login and on every admin role change, so a
  manipulated frontend request cannot escalate privileges.
- **Password reset** — 32-byte `secrets.token_urlsafe` tokens, single-use,
  1-hour expiry, previous tokens invalidated on re-request, per-email rate
  limiting (3 / 15 min), and a deliberately generic response so account
  existence cannot be probed.
- **Session invalidation** — every reset bumps the user's `password_version`;
  JWTs carry it and tokens minted before the reset are rejected immediately.
- **Chatbot key safety** — `OPENAI_API_KEY` lives only in the backend
  environment; the browser never sees it.
- **CORS** — permissive in dev; set `CORS_ORIGINS=https://your-frontend` in
  production.

> `bcrypt` is pinned to **4.0.1**: version 5.x removed the `__about__`
> attribute that `passlib` 1.7.4 reads, causing a crash on password hashing.

---

## Team

**Fraud Hawks** — عبدالله العامري · معاذ نافيد · محمد آل سعيد
