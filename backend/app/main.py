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
from app.routers import auth, sms, transactions, alerts, dashboard
from app.ml.sms_classifier import model_status

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Creates tables on startup if they don't exist yet (fine for MVP/hackathon;
# use Alembic migrations for production).
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Report which SMS backend is live at startup. Do not skip this: if the
    trained model is missing, the app still runs on rules -- and you would
    otherwise demo the wrong thing without noticing.

    Loading here (not on first request) also means the ~1.1GB model is warm
    before the demo, so the first SMS check isn't slow.
    """
    status = model_status()
    if status["backend"] == "transformer":
        logger.info("SMS model: TRANSFORMER active (%s, device=%s)",
                    status["model_dir"], status["device"])
    else:
        logger.warning("SMS model: RULE ENGINE active -- %s. "
                       "The trained model is NOT being used.",
                       status.get("reason", ""))
    yield


app = FastAPI(
    title="Alinma SecureAI",
    description="Intelligent Fraud & Scam Prevention Platform for Alinma Bank",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS: allow the React frontend (running on a different port) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this to your frontend's real origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sms.router)
app.include_router(transactions.router)
app.include_router(alerts.router)
app.include_router(dashboard.router)


@app.get("/", tags=["Health"])
def health_check():
    """Health + which SMS model backend is serving (verify before demoing)."""
    return {
        "status": "ok",
        "service": "Alinma SecureAI API",
        "sms_model": model_status(),
    }
