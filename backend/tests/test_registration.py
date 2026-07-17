"""
Integration tests for the POST /auth/register endpoint.

Covers:
  - Successful registration returns a JWT
  - Role cannot be injected via the request body (account is always 'customer')
  - Duplicate email is rejected with 409
  - Staff email (@alinma.com) is blocked with 403
  - Short password is rejected with 422 (Pydantic validation)
"""
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app import models, auth as auth_module


# ---------------------------------------------------------------------------
# In-memory SQLite test database
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
    """Recreate all tables before each test.

    The get_db override is (re)applied here rather than at import time:
    every test module has its own in-memory engine, and a module-level
    assignment would let the last-imported module win for the whole run.
    """
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


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


VALID_PAYLOAD = {
    "name": "Alice Customer",
    "email": "alice@example.com",
    "phone": "+966500000001",
    "password": "SecurePass1!",
}


# ===========================================================================
# POST /auth/register — happy path
# ===========================================================================

class TestRegisterSuccess:
    def test_successful_registration_returns_201(self, client):
        resp = client.post("/auth/register", json=VALID_PAYLOAD)
        assert resp.status_code == 201

    def test_successful_registration_returns_jwt(self, client):
        resp = client.post("/auth/register", json=VALID_PAYLOAD)
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert len(body["access_token"]) > 0

    def test_jwt_is_valid_and_accepted_by_me_endpoint(self, client):
        """The returned token must be accepted by GET /auth/me."""
        resp = client.post("/auth/register", json=VALID_PAYLOAD)
        token = resp.json()["access_token"]
        me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.status_code == 200

    def test_registered_user_data_is_correct(self, client):
        """GET /auth/me must return matching name, email, and customer role."""
        resp = client.post("/auth/register", json=VALID_PAYLOAD)
        token = resp.json()["access_token"]
        me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
        assert me["name"] == VALID_PAYLOAD["name"]
        assert me["email"] == VALID_PAYLOAD["email"]
        assert me["role"] == "customer"

    def test_registration_without_phone_succeeds(self, client):
        """phone is optional — omitting it must still return 201."""
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "phone"}
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 201

    def test_user_is_persisted_in_db(self, client, db):
        client.post("/auth/register", json=VALID_PAYLOAD)
        user = db.query(models.User).filter_by(email=VALID_PAYLOAD["email"]).first()
        assert user is not None
        assert user.name == VALID_PAYLOAD["name"]


# ===========================================================================
# Role cannot be injected at registration
# ===========================================================================

class TestRoleCannotBeInjected:
    def test_role_field_in_body_is_ignored(self, client):
        """Passing role='analyst' must have no effect — account is always 'customer'."""
        payload = {**VALID_PAYLOAD, "role": "analyst"}
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 201
        token = resp.json()["access_token"]
        me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
        assert me["role"] == "customer", (
            "Role must always be 'customer' regardless of what was submitted"
        )

    def test_role_admin_in_body_is_ignored(self, client):
        """Passing role='admin' must be silently discarded."""
        payload = {**VALID_PAYLOAD, "role": "admin"}
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 201
        token = resp.json()["access_token"]
        me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
        assert me["role"] == "customer"

    def test_role_stored_in_db_is_customer(self, client, db):
        """Regardless of request body, the DB must store role=customer."""
        payload = {**VALID_PAYLOAD, "role": "admin"}
        client.post("/auth/register", json=payload)
        user = db.query(models.User).filter_by(email=VALID_PAYLOAD["email"]).first()
        assert user is not None
        assert user.role == models.UserRole.customer


# ===========================================================================
# Validation and conflict errors
# ===========================================================================

class TestRegisterErrors:
    def test_duplicate_email_returns_409(self, client):
        client.post("/auth/register", json=VALID_PAYLOAD)
        resp = client.post("/auth/register", json=VALID_PAYLOAD)
        assert resp.status_code == 409

    def test_staff_email_is_blocked_with_403(self, client):
        payload = {**VALID_PAYLOAD, "email": "alice@alinma.com"}
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 403

    def test_short_password_rejected_with_422(self, client):
        """Pydantic min_length=8 must reject short passwords before any DB access."""
        payload = {**VALID_PAYLOAD, "password": "short"}
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 422

    def test_missing_email_rejected_with_422(self, client):
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "email"}
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 422

    def test_missing_name_rejected_with_422(self, client):
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "name"}
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 422
