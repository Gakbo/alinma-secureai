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
| 1 | **SMS Scanner** — paste an Arabic/English SMS, get a risk score + plain-language reason | ✅ trained XLM-RoBERTa |
| 2 | **Transfer Guardian** — score a transfer before it sends | ✅ explainable rule engine ([why](#honest-limitations)) |
| 3 | **Fraud Alerts** — high-risk events auto-generate alerts | ✅ |
| 4 | **Customer Security Score** — behaviour, device trust, scam exposure | ✅ |
| 5 | **Analyst Dashboard** — live stats, severity/attack-type charts, high-risk customers | ✅ Chart.js |

Every risk verdict ships with a **human-readable explanation** (FR7). The model
supplies the score; a transparent rule layer supplies the *reason*. A customer
cannot act on "0.87 fraud probability" — they can act on *"this impersonates
Alinma Bank and contains an unrecognised link."*

---

## Architecture

```
                    React + Tailwind (Axios)
                              |
                         FastAPI + JWT
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       SMS Scanner     Transfer Guardian   Dashboard
              |               |               |
        XLM-RoBERTa     Rule engine      Chart.js
              └───────► Explanation ◄────────┘
                              |
                    PostgreSQL / SQLite
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
│   └── saved_models/   Trained model artifacts (gitignored, ~1.1GB)
├── frontend/           React + Tailwind + Axios + Chart.js
├── ml-training/        Config-driven training pipeline
│   ├── config/         training_config.yaml — switch models without code edits
│   ├── sms_model/      Registry, validation, imbalance, augmentation, benchmark
│   └── fraud_model/    XGBoost + Isolation Forest
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
pip install torch --index-url https://download.pytorch.org/whl/cpu
python seed_data.py
uvicorn app.main:app --reload
```

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
If it says `"backend": "rules"`, the trained model is **not** loaded — see
[Deploying a trained model](#deploying-a-trained-model).

**Demo accounts** (from `seed_data.py`):

| Role | Email | Password |
|---|---|---|
| customer | sara.customer@example.com | Password123 |
| analyst | analyst@alinma.com | Password123 |

**Docker:**
```bash
docker compose up --build          # frontend :3000 · backend :8000 · PostgreSQL
docker compose exec backend python seed_data.py
```

---

## Demo script (3 minutes)

1. **Phishing SMS** — sign in as Sara → *SMS Scanner* → "Use demo phishing
   sample" → **Fraud, 100/100**, with the reason spelled out. An alert is
   generated automatically.
2. **High-risk transfer** — *Transfer Guardian* → "Use demo high-risk transfer"
   (SAR 20,000, new beneficiary, foreign destination) → **High risk, 90/100 —
   recommend blocking.**
3. **Explanation** — both panels answer *why*, in plain language, not just a score.
4. **Analyst view** — sign in as the analyst → *Dashboard*: live counts, alerts
   by severity and attack type, high-risk customers.

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

- **Transaction risk uses rules, not the trained XGBoost model.** The XGBoost
  pipeline is built and integrated (`TXN_MODEL_BACKEND=model` enables it), but
  it was trained on *synthetic* data generated by our own rules — so it largely
  re-learned those rules, and its near-perfect score on that data is circular.
  It also leans on `prior_transaction_count`, which our backend does not yet
  track. Shipping the rule engine is the honest choice; the model swaps in the
  moment real transaction data exists.
- **The Arabic evaluation set is small** (~93 messages in the test split). The
  98.5% F1 is genuine but rests on a narrow sample. More Arabic data is our top
  priority.
- **No real code-switched data.** The "mixed" slice is our own synthetic
  templates, so we do not quote it.
- **English data is 2011 UK generic spam**, not bank phishing — it broadens
  coverage but does not represent Saudi banking threats.
- **Model C (Isolation Forest)** is trained but not wired into the backend.

---

## Security

bcrypt password hashing · JWT auth with role-based access
(customer/analyst/admin) · SQLAlchemy ORM (parameterised queries → SQL
injection protection) · secrets via environment variables (`.env`, gitignored)
· CORS configured · HTTPS/TLS assumed at deployment.

> `bcrypt` is pinned to **4.0.1**: version 5.x removed the `__about__`
> attribute that `passlib` 1.7.4 reads, causing a crash on password hashing.

---

## Team

**Fraud Hawks** — عبدالله العامري · معاذ نافيد · محمد آل سعيد
