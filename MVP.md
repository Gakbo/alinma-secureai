# Alinma SecureAI — MVP

**Intelligent Fraud & Scam Prevention System for Alinma Bank**
AMAD Fintech Hackathon (Alinma Bank × Tuwaiq Academy) · Team *Fraud Hawks*

---

## 1. One-line pitch

Alinma SecureAI stops fraud **before** money moves — it scores a suspicious SMS
before the customer clicks and a transfer before the funds leave the account,
and explains *why* in plain Arabic or English.

## 2. Problem

Digital banking in Saudi Arabia is growing fast, exposing customers to phishing
SMS, fake banking sites, social-engineering, account takeover, and unauthorized
transactions. Existing fraud systems are **reactive** — they flag activity
*after* the loss. That means customer financial loss, reduced trust, and higher
investigation cost for the bank.

## 3. Solution

An AI-powered, **prevention-first** platform built for Alinma Bank's digital
ecosystem. It combines Machine Learning, NLP, and behavioural analytics to catch
fraud at the two moments it actually happens — the phishing message and the
outgoing transfer — and returns a human-readable reason a customer can act on.
Fully bilingual (Arabic/English) with RTL support for the Saudi market.

---

## 4. Hackathon MVP scope (per the AMAD brief)

The AMAD project brief defines the MVP as five must-build capabilities plus
optional stretch items. **All are delivered.**

| MVP requirement | Status |
|-----------------|--------|
| **Login** (secure auth) | ✅ Done — JWT + bcrypt, role-based |
| **SMS Detector** (phishing detection AR/EN) | ✅ Done — 3-tier ML + explanation |
| **Transaction Checker** (risk analysis) | ✅ Done — XGBoost + rule explanation |
| **Dashboard** (analyst fraud view) | ✅ Done — trends, charts, high-risk users |
| **AI Explanation** (why each verdict) | ✅ Done — plain-language reason on every score |
| *Optional:* Security Score | ✅ Done |
| *Optional:* Alert History | ✅ Done — with filters & acknowledge/resolve |
| *Optional:* Notifications | ✅ Done — fraud-alert emails |

### Delivered beyond the required MVP

- **AI banking assistant** — floating bilingual chatbot (OpenAI + rule-based IVR fallback)
- **Customer self-signup** with server-enforced staff-domain block
- **Forgot / reset password** with token expiry + session invalidation (`password_version`)
- **Admin panel** — user & role management with domain guard
- **Full Arabic/English UI** with live RTL↔LTR switching across every page

---

## 5. Core features

| # | Feature | What it does | Backing |
|---|---------|--------------|---------|
| 1 | **SMS Scanner** | Paste an AR/EN SMS → safe / suspicious / fraud + score + reason | XLM-RoBERTa → TF-IDF → rules |
| 2 | **Transfer Guardian** | Score a transfer before sending → approve / verify / reject | XGBoost + rule layer |
| 3 | **Fraud Alerts** | High-risk events auto-alert; filter, acknowledge (customer), resolve (analyst) | Persisted, role-scoped |
| 4 | **Security Score** | Behaviour, device-trust, scam-exposure + grade & recommendations | Per-user scoring |
| 5 | **Analyst Dashboard** | 7-day trend, severity / type / region charts, high-risk customers | Chart.js |
| 6 | **AI Assistant** | 7 guided topics + free-text, bilingual | OpenAI `gpt-4o-mini` + IVR fallback |
| 7 | **Auth & Signup** | Login, customer signup, `@alinma.com` staff guard | JWT · bcrypt · server-enforced |
| 8 | **Password Reset** | Emailed single-use token, expiry, rate-limit, old-session kill | `password_version` in JWT |
| 9 | **Admin Panel** | User list + inline role changes, domain guard | Admin-only |

Every verdict ships with a **human-readable explanation** (FR7) — a customer
can't act on "0.87 fraud probability" but can act on *"this impersonates Alinma
Bank and contains an unrecognised link."*

---

## 6. Alignment with AMAD challenge tracks

| Track | Fit |
|-------|-----|
| **Cybersecurity** (primary) | Fraud/phishing prevention, secure auth, session invalidation, anomaly signals |
| **Financial Analytics** | Transaction risk scoring, analyst dashboard, fraud trends & region stats |
| **Financial Education** | AI assistant teaching customers to spot scams and protect OTPs |
| **Financial Inclusion** | Full Arabic + English + RTL — accessible to all Saudi customers |

---

## 7. Tech stack

**Frontend** React · Vite · Tailwind CSS · Axios · Chart.js · React Router
**Backend** Python · FastAPI · Uvicorn · SQLAlchemy · Pydantic · JWT · bcrypt
**ML** PyTorch + Transformers (XLM-RoBERTa) · scikit-learn (TF-IDF) · XGBoost
**AI** OpenAI `gpt-4o-mini` (optional) + rule-based bilingual fallback
**Data** PostgreSQL (prod) / SQLite (dev) · SMTP email
**Infra** Docker Compose (frontend + backend + PostgreSQL)

## 8. Architecture

```
        React + Tailwind + Vite (Axios · EN/AR · RTL)
                          |
                     FastAPI + JWT
  ┌──────────┬───────────┼───────────┬──────────┐
  ▼          ▼           ▼           ▼          ▼
 SMS      Transfer   Dashboard    AI Chat    Admin /
 Scanner  Guardian   + Alerts    Assistant    Auth
  |          |           |           |          |
XLM-R/     XGBoost   Chart.js   OpenAI+IVR  bcrypt +
TF-IDF     + rules                rules    pwd_version
+ rules
  └──────────┴─► Explanation ◄┘
                          |
                PostgreSQL / SQLite
                          |
             SMTP (reset + alert emails,
              console fallback in dev)
```

## 9. Success criteria (acceptance)

- [x] Customer registers, logs in, logs out; staff domain enforced.
- [x] SMS scan returns score + reason for Arabic and English.
- [x] Transfer scan returns approve / verify / reject with explanation.
- [x] High-risk events create alerts; acknowledge/resolve persist across refresh.
- [x] Security Score reflects the user's live risk profile.
- [x] Analyst dashboard renders from live data; blocked for customers.
- [x] Chatbot answers in both languages, with and without an OpenAI key.
- [x] Forgot/reset works; old JWTs rejected after reset.
- [x] Admin changes roles; privilege escalation blocked server-side.
- [x] Whole UI switches EN⇄AR with correct RTL/LTR.
- [x] Frontend production build succeeds; backend starts; 42 pytest + 56 API checks pass.

## 10. Demo flow (~4 min)

1. Customer → **SMS Scanner** → demo phishing → *Fraud ~98/100* + reason (alert auto-created).
2. **Transfer Guardian** → large foreign transfer → *High risk — recommend blocking*.
3. **AI Assistant** → type `2` → phishing guidance → toggle عربي → app flips to Arabic RTL.
4. **Security Score** → grade + animated ring scores + recommendations.
5. **Fraud Alerts** → acknowledge → "Seen" badge survives refresh.
6. Analyst → **Dashboard**: trend, charts, high-risk customers.
7. Admin → **Admin Panel** → change a role (domain guard enforced).
8. **Forgot password** → reset link in backend console → new password → old session invalid.

## 11. Out of scope (post-MVP)

- Real Alinma transaction/customer data (models retrain-ready, zero code change).
- Real-time streaming ingestion of live transactions.
- Native mobile apps (web is responsive, browser-only).
- Model C (Isolation Forest) — trained but not wired into the backend.
- Production email at scale / shared (Redis) rate-limit store.
- SSO / hardware MFA.

## 12. How to run

```bash
# Backend
cd backend && py -3.12 -m venv venv && .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python seed_data.py          # demo data (drops & recreates tables)
python train_models.py       # optional: TF-IDF + XGBoost in ~1 min, no GPU
uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev     # http://localhost:5173

# Or Docker
docker compose up --build
```

**Demo accounts** (`seed_data.py`, password `Password123`):
`sara.customer@example.com` · `analyst@alinma.com` · `admin@alinma.com`

## 13. Status

**MVP complete and verified.** All five required capabilities plus every optional
item delivered; 42 backend tests and 56 live API checks pass; frontend production
build succeeds; end-to-end flows verified in-browser (AR/EN, RTL/LTR, all roles).

> Honest limitations (synthetic-trained transaction model, small Arabic eval set,
> in-memory rate limiter) are documented in [README.md](README.md).
