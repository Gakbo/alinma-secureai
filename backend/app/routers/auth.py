import secrets
import threading
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import models, schemas, auth
from app.database import get_db
from app.email_utils import send_password_reset_email

router = APIRouter(prefix="/auth", tags=["Authentication"])

RESET_TOKEN_EXPIRE_HOURS = 1
STAFF_DOMAIN = "@alinma.com"

# Rate-limit: at most this many reset requests per email per window.
# Tracked in-memory (not in DB) so it applies to ALL emails regardless of
# whether they belong to a registered account — this preserves the
# anti-enumeration guarantee (both registered and unregistered emails hit
# the same 429 response path after RESET_RATE_LIMIT attempts).
RESET_RATE_LIMIT = 3
RESET_RATE_WINDOW_MINUTES = 15

_reset_attempts: dict = {}        # email -> list[datetime] of attempt timestamps
_reset_attempts_lock = threading.Lock()


def _check_and_record_reset_attempt(email: str) -> None:
    """
    Raises HTTP 429 if the email has hit the rate limit within the current
    window.  Records the attempt unconditionally for ALL emails so that
    registered and unregistered addresses are indistinguishable to callers.
    """
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=RESET_RATE_WINDOW_MINUTES)

    with _reset_attempts_lock:
        attempts = _reset_attempts.get(email, [])
        # Drop timestamps that have aged out of the window
        attempts = [t for t in attempts if t >= window_start]
        if len(attempts) >= RESET_RATE_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many reset requests. Try again in {RESET_RATE_WINDOW_MINUTES} minutes.",
            )
        attempts.append(now)
        _reset_attempts[email] = attempts


def _is_staff_email(email: str) -> bool:
    return email.lower().endswith(STAFF_DOMAIN)


@router.post("/register", response_model=schemas.Token, status_code=status.HTTP_201_CREATED)
def register(user_in: schemas.RegisterRequest, db: Session = Depends(get_db)):
    """
    Self-registration for bank customers. Always creates a 'customer' role
    account — role cannot be set at registration.
    Returns a JWT token immediately so the user is logged in on signup.
    """
    # Block Alinma staff emails from self-registration — accounts are IT-managed.
    if _is_staff_email(user_in.email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Alinma staff accounts are managed by IT. Use the Staff Login tab with your @alinma.com email.",
        )

    existing = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = models.User(
        name=user_in.name,
        email=user_in.email,
        phone=user_in.phone,
        hashed_password=auth.hash_password(user_in.password),
        role=models.UserRole.customer,   # always customer — role cannot be set on signup
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = auth.create_access_token(
        data={"sub": user.user_id, "role": user.role, "pwd_v": user.password_version}
    )
    return schemas.Token(access_token=access_token)


@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Uses OAuth2PasswordRequestForm (standard FastAPI login form: username + password)
    — pass the user's email in the `username` field.
    """
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Enforce domain-role consistency as a backend safety net.
    is_staff = _is_staff_email(user.email)
    if is_staff and user.role == "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This is an Alinma staff email. Please use the Staff Login tab.",
        )
    if not is_staff and user.role in ("analyst", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff accounts must use an @alinma.com email address. Contact IT if this is unexpected.",
        )

    access_token = auth.create_access_token(
        data={"sub": user.user_id, "role": user.role, "pwd_v": user.password_version}
    )
    return schemas.Token(access_token=access_token)


@router.get("/me", response_model=schemas.UserOut)
def read_current_user(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


# ---------------------------------------------------------------------------
# Password reset — token-based, self-service
# ---------------------------------------------------------------------------

@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(body: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Request a password-reset email. Returns 429 when the per-email rate limit
    is exceeded (applies to registered and unregistered addresses alike to
    prevent account enumeration via differential responses). Otherwise always
    returns 202 regardless of whether the email is registered.
    In development (no SMTP configured), the reset link is printed to the
    server console.
    """
    # Rate-limit before any DB lookup so registered/unregistered emails are
    # treated identically and cannot be distinguished by response behavior.
    _check_and_record_reset_attempt(body.email)

    user = db.query(models.User).filter(models.User.email == body.email).first()
    if user:
        # Invalidate any existing unused tokens for this email
        db.query(models.PasswordReset).filter(
            models.PasswordReset.email == body.email,
            models.PasswordReset.used == 0,
        ).update({"used": 1})
        db.commit()

        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=RESET_TOKEN_EXPIRE_HOURS)
        reset = models.PasswordReset(
            email=body.email,
            token=token,
            expires_at=expires_at,
        )
        db.add(reset)
        db.commit()

        try:
            send_password_reset_email(body.email, token)
        except Exception:
            # Email sending failed — don't expose the error to the caller
            pass

    return {"detail": "If that email is registered, a reset link has been sent."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(body: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Consume a reset token and set a new password.
    Invalidates the token and bumps password_version to expire old sessions.
    """
    reset = db.query(models.PasswordReset).filter(
        models.PasswordReset.token == body.token,
    ).first()

    if not reset or reset.used or reset.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset link is invalid or has expired. Please request a new one.",
        )

    user = db.query(models.User).filter(models.User.email == reset.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset link is invalid or has expired. Please request a new one.",
        )

    # Update password and bump version to invalidate old JWTs
    user.hashed_password = auth.hash_password(body.new_password)
    user.password_version = (user.password_version or 0) + 1
    reset.used = 1
    db.commit()

    return {"detail": "Password updated successfully. Please log in with your new password."}
