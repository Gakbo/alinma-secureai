"""
Admin-only endpoints.
All routes require the 'admin' JWT role — any other role gets 403.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app import models, schemas, auth
from app.database import get_db

router = APIRouter(prefix="/admin", tags=["Admin"])

# Dependency: enforce admin role
require_admin = auth.require_role("admin")


@router.get("/users", response_model=List[schemas.UserListItem])
def list_users(
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    """Return all users ordered by creation date (newest first)."""
    return (
        db.query(models.User)
        .order_by(models.User.created_at.desc())
        .all()
    )


@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: str,
    body: schemas.RoleUpdate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
):
    """Change a user's role. Allowed values: customer, analyst, admin."""
    allowed = [r.value for r in models.UserRole]
    if body.role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role must be one of: {allowed}",
        )

    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Domain-role mismatch guard
    STAFF_DOMAIN = "@alinma.com"
    is_staff_email = user.email.lower().endswith(STAFF_DOMAIN)
    is_staff_role = body.role in ("analyst", "admin")

    if is_staff_email and not is_staff_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot assign role '{body.role}' to a {STAFF_DOMAIN} account. "
                f"Staff email addresses must keep an analyst or admin role."
            ),
        )
    if not is_staff_email and is_staff_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot assign role '{body.role}' to a non-{STAFF_DOMAIN} account. "
                f"Only {STAFF_DOMAIN} email addresses may hold analyst or admin roles."
            ),
        )

    user.role = body.role
    db.commit()
    db.refresh(user)
    return {"user_id": user.user_id, "name": user.name, "role": user.role}
