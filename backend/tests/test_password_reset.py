"""
Integration tests for the password-reset flow.

Covers:
  - POST /auth/forgot-password: known email, unknown email, duplicate requests
  - POST /auth/reset-password: valid token, expired token, already-used token,
    short password
  - Old JWT is rejected after a password reset (password_version mismatch)
"""
import pytest
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app import models, auth as auth_module
from app.routers.auth import _reset_attempts, _reset_attempts_lock


# ---------------------------------------------------------------------------
# In-memory SQLite test database
#
# StaticPool makes every SQLAlchemy request reuse the *same* underlying
# connection, so `create_all` in the fixture and the per-request session
# (injected via the dependency override) both see the same in-memory DB.
# ---------------------------------------------------------------------------

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def fresh_db():
    """Recreate all tables before each test and wipe rate-limit state.

    The get_db override is (re)applied here rather than at import time:
    every test module has its own in-memory engine, and a module-level
    assignment would let the last-imported module win for the whole run.
    """
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    # Clear the in-memory rate-limit store between tests.
    with _reset_attempts_lock:
        _reset_attempts.clear()


@pytest.fixture()
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture()
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def customer(db):
    """Create and return a plain customer user."""
    user = models.User(
        name="Test Customer",
        email="customer@example.com",
        hashed_password=auth_module.hash_password("OldPassword1!"),
        role=models.UserRole.customer,
        password_version=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_reset_token(db, email: str, *, used: bool = False,
                       expired: bool = False) -> str:
    """Insert a PasswordReset row and return its token string."""
    import secrets
    token = secrets.token_urlsafe(32)
    if expired:
        expires_at = datetime.utcnow() - timedelta(hours=2)
    else:
        expires_at = datetime.utcnow() + timedelta(hours=1)

    reset = models.PasswordReset(
        email=email,
        token=token,
        expires_at=expires_at,
        used=1 if used else 0,
    )
    db.add(reset)
    db.commit()
    return token


# ===========================================================================
# POST /auth/forgot-password
# ===========================================================================

class TestForgotPassword:
    def test_known_email_returns_202(self, client, customer):
        resp = client.post("/auth/forgot-password", json={"email": customer.email})
        assert resp.status_code == 202

    def test_unknown_email_also_returns_202(self, client):
        """Anti-enumeration: unregistered addresses must get the same 202."""
        resp = client.post(
            "/auth/forgot-password", json={"email": "nobody@example.com"}
        )
        assert resp.status_code == 202

    def test_response_body_is_generic(self, client, customer):
        """Response must not reveal whether the email is registered."""
        resp = client.post("/auth/forgot-password", json={"email": customer.email})
        assert "reset link" in resp.json()["detail"].lower()

    def test_token_created_in_db_for_known_email(self, client, customer, db):
        client.post("/auth/forgot-password", json={"email": customer.email})
        reset = (
            db.query(models.PasswordReset)
            .filter_by(email=customer.email, used=0)
            .first()
        )
        assert reset is not None, "A fresh unused token should be stored in the DB"

    def test_no_token_created_for_unknown_email(self, client, db):
        client.post("/auth/forgot-password", json={"email": "ghost@example.com"})
        count = (
            db.query(models.PasswordReset)
            .filter_by(email="ghost@example.com")
            .count()
        )
        assert count == 0

    def test_duplicate_request_invalidates_previous_token(
        self, client, customer, db
    ):
        """A second forgot-password for the same email must burn the first token."""
        client.post("/auth/forgot-password", json={"email": customer.email})
        first_token = (
            db.query(models.PasswordReset)
            .filter_by(email=customer.email, used=0)
            .first()
        )
        assert first_token is not None

        client.post("/auth/forgot-password", json={"email": customer.email})
        db.expire_all()  # re-read from DB
        invalidated = (
            db.query(models.PasswordReset)
            .filter_by(token=first_token.token)
            .first()
        )
        assert invalidated.used == 1, "The first token should now be marked used"

        # A fresh valid token should exist
        fresh = (
            db.query(models.PasswordReset)
            .filter_by(email=customer.email, used=0)
            .first()
        )
        assert fresh is not None
        assert fresh.token != first_token.token


# ===========================================================================
# POST /auth/reset-password
# ===========================================================================

class TestResetPassword:
    def test_valid_token_returns_200(self, client, customer, db):
        token = _make_reset_token(db, customer.email)
        resp = client.post(
            "/auth/reset-password",
            json={"token": token, "new_password": "NewPassword1!"},
        )
        assert resp.status_code == 200

    def test_valid_token_updates_password(self, client, customer, db):
        token = _make_reset_token(db, customer.email)
        client.post(
            "/auth/reset-password",
            json={"token": token, "new_password": "BrandNew99!"},
        )
        db.expire_all()
        updated_user = db.query(models.User).filter_by(email=customer.email).first()
        assert auth_module.verify_password("BrandNew99!", updated_user.hashed_password)

    def test_valid_token_is_marked_used_after_reset(self, client, customer, db):
        token = _make_reset_token(db, customer.email)
        client.post(
            "/auth/reset-password",
            json={"token": token, "new_password": "NewPassword1!"},
        )
        db.expire_all()
        reset = db.query(models.PasswordReset).filter_by(token=token).first()
        assert reset.used == 1

    def test_expired_token_returns_400(self, client, customer, db):
        token = _make_reset_token(db, customer.email, expired=True)
        resp = client.post(
            "/auth/reset-password",
            json={"token": token, "new_password": "NewPassword1!"},
        )
        assert resp.status_code == 400

    def test_already_used_token_returns_400(self, client, customer, db):
        token = _make_reset_token(db, customer.email, used=True)
        resp = client.post(
            "/auth/reset-password",
            json={"token": token, "new_password": "NewPassword1!"},
        )
        assert resp.status_code == 400

    def test_nonexistent_token_returns_400(self, client):
        resp = client.post(
            "/auth/reset-password",
            json={"token": "completely-bogus-token", "new_password": "NewPassword1!"},
        )
        assert resp.status_code == 400

    def test_short_password_rejected_before_db_lookup(self, client, customer, db):
        """Pydantic min_length=8 must reject short passwords with 422."""
        token = _make_reset_token(db, customer.email)
        resp = client.post(
            "/auth/reset-password",
            json={"token": token, "new_password": "short"},
        )
        assert resp.status_code == 422

    def test_used_token_cannot_be_replayed(self, client, customer, db):
        """Using a token twice must fail on the second attempt."""
        token = _make_reset_token(db, customer.email)
        client.post(
            "/auth/reset-password",
            json={"token": token, "new_password": "FirstReset1!"},
        )
        resp = client.post(
            "/auth/reset-password",
            json={"token": token, "new_password": "SecondReset1!"},
        )
        assert resp.status_code == 400


# ===========================================================================
# password_version — old JWT rejected after reset
# ===========================================================================

class TestPasswordVersionInvalidatesOldJwt:
    def test_old_jwt_rejected_after_password_reset(self, client, customer, db):
        """
        A JWT minted before a password reset must be rejected by /auth/me
        because the token's pwd_v no longer matches the user's password_version.
        """
        # 1. Mint a JWT at the current password_version (0).
        old_token = auth_module.create_access_token(
            data={
                "sub": customer.user_id,
                "role": str(customer.role),
                "pwd_v": customer.password_version,  # 0
            }
        )

        # 2. Perform a password reset (bumps password_version to 1).
        reset_token = _make_reset_token(db, customer.email)
        resp = client.post(
            "/auth/reset-password",
            json={"token": reset_token, "new_password": "AfterReset99!"},
        )
        assert resp.status_code == 200

        # 3. The old JWT must now be rejected.
        me_resp = client.get(
            "/auth/me", headers={"Authorization": f"Bearer {old_token}"}
        )
        assert me_resp.status_code == 401, (
            "Old JWT (pwd_v=0) must be rejected after password reset bumped "
            "password_version to 1"
        )

    def test_new_jwt_accepted_after_password_reset(self, client, customer, db):
        """
        A JWT minted *after* a password reset (with the updated pwd_v) must
        be accepted by /auth/me.
        """
        # Perform reset
        reset_token = _make_reset_token(db, customer.email)
        client.post(
            "/auth/reset-password",
            json={"token": reset_token, "new_password": "AfterReset99!"},
        )

        # Mint a fresh JWT with the new password_version
        db.expire_all()
        updated_user = db.query(models.User).filter_by(email=customer.email).first()
        new_token = auth_module.create_access_token(
            data={
                "sub": updated_user.user_id,
                "role": str(updated_user.role),
                "pwd_v": updated_user.password_version,  # now 1
            }
        )

        me_resp = client.get(
            "/auth/me", headers={"Authorization": f"Bearer {new_token}"}
        )
        assert me_resp.status_code == 200

    def test_password_version_incremented_on_reset(self, client, customer, db):
        """password_version must increment by exactly 1 after each reset."""
        initial_version = customer.password_version  # 0

        reset_token = _make_reset_token(db, customer.email)
        client.post(
            "/auth/reset-password",
            json={"token": reset_token, "new_password": "AfterReset99!"},
        )

        db.expire_all()
        updated_user = db.query(models.User).filter_by(email=customer.email).first()
        assert updated_user.password_version == initial_version + 1
