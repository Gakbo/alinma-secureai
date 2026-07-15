"""
Database configuration.

Defaults to SQLite (./alinma_secureai.db) so the project runs with zero
extra setup. To switch to PostgreSQL for production, just set the
DATABASE_URL environment variable, e.g.:

    postgresql://alinma_user:password@localhost:5432/alinma_secureai

No code changes are needed to switch databases.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./alinma_secureai.db")

# SQLite needs this connect_arg; Postgres does not.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
