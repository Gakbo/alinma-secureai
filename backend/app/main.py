"""
Alinma SecureAI — FastAPI backend entry point.

Run with:
    uvicorn app.main:app --reload

Then open http://127.0.0.1:8000/docs for interactive API docs (Swagger UI).
"""
from dotenv import load_dotenv
load_dotenv()

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth, sms, transactions, alerts, dashboard, admin, chat
from app.ml.sms_classifier import model_status
from app.ml.transaction_risk import txn_model_status
from app.email_utils import check_email_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Creates tables on startup if they don't exist yet (fine for MVP/hackathon;
# use Alembic migrations for production).
Base.metadata.create_all(bind=engine)

# Lightweight schema migrations: add new columns to existing tables when they
# don't exist yet. SQLAlchemy's create_all() only creates missing tables, not
# missing columns, so we handle new columns here.
from sqlalchemy import text, inspect as sa_inspect
with engine.connect() as _conn:
    _insp = sa_inspect(engine)
    _user_cols = {c["name"] for c in _insp.get_columns("users")}
    if "password_version" not in _user_cols:
        _conn.execute(text("ALTER TABLE users ADD COLUMN password_version INTEGER NOT NULL DEFAULT 0"))
        _conn.commit()

    _alert_cols = {c["name"] for c in _insp.get_columns("alerts")}
    if "acknowledged_by_customer" not in _alert_cols:
        _conn.execute(text("ALTER TABLE alerts ADD COLUMN acknowledged_by_customer BOOLEAN NOT NULL DEFAULT FALSE"))
        _conn.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Report which SMS backend is live at startup. Do not skip this: if the
    trained model is missing, the app still runs on rules -- and you would
    otherwise demo the wrong thing without noticing.

    Loading here (not on first request) also means the ~1.1GB model is warm
    before the demo, so the first SMS check isn't slow.
    """
    # ── SMS model ──────────────────────────────────────────────────────────
    sms = model_status()
    if sms["backend"] == "transformer":
        logger.info("SMS model: TRANSFORMER active (%s, device=%s)",
                    sms["model_dir"], sms.get("device", "cpu"))
    elif sms["backend"] == "tfidf":
        logger.info("SMS model: TF-IDF ML active (AUC=0.9991, dir=%s)",
                    sms["model_dir"])
    else:
        logger.warning("SMS model: RULE ENGINE only — %s", sms.get("reason", ""))

    # ── Transaction model ──────────────────────────────────────────────────
    txn = txn_model_status()
    if txn["backend"] == "xgboost":
        logger.info("Transaction model: XGBOOST active (%s)", txn["model_file"])
    else:
        logger.warning("Transaction model: RULE ENGINE only — %s",
                       txn.get("reason", ""))

    # ── Email / SMTP ────────────────────────────────────────────────────────
    email_cfg = check_email_config()
    if email_cfg["configured"]:
        import os as _os
        logger.info(
            "Email: SMTP configured — host=%s port=%s from=%s app_url=%s",
            _os.getenv("SMTP_HOST", "smtp.gmail.com"),
            _os.getenv("SMTP_PORT", "587"),
            _os.getenv("SMTP_FROM") or _os.getenv("SMTP_USER", ""),
            _os.getenv("APP_URL", "http://localhost:5173"),
        )
        for warn in email_cfg["warnings"]:
            logger.warning("Email config warning: %s", warn)
    else:
        logger.warning(
            "Email: SMTP not configured — missing env vars: %s.\n"
            "        Password-reset and fraud-alert emails will NOT be "
            "delivered to real users.\n"
            "        In development, reset links are printed to this console "
            "instead. Set the SMTP_* variables in backend/.env for real "
            "delivery — see docs/smtp-setup.md for instructions.",
            ", ".join(email_cfg["missing"]),
        )

    yield


app = FastAPI(
    title="Alinma SecureAI",
    description="Intelligent Fraud & Scam Prevention Platform for Alinma Bank",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS: allow the React frontend (running on a different port) to call this API.
# Dev default is permissive; set CORS_ORIGINS to a comma-separated list of real
# origins in production, e.g. CORS_ORIGINS=https://secureai.example.com
import os as _os
_cors_origins = [o.strip() for o in _os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sms.router)
app.include_router(transactions.router)
app.include_router(alerts.router)
app.include_router(dashboard.router)
app.include_router(admin.router)
app.include_router(chat.router)


@app.get("/", tags=["Health"])
def health_check():
    """Health + which SMS model backend is serving (verify before demoing)."""
    return {
        "status": "ok",
        "service": "Alinma SecureAI API",
        "sms_model": model_status(),
    }
