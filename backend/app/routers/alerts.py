from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas, auth
from app.database import get_db

router = APIRouter(prefix="/alerts", tags=["Fraud Alerts"])


@router.get("/", response_model=List[schemas.AlertOut])
def list_alerts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Customers see only their own alerts; analysts/admins see all alerts."""
    query = db.query(models.Alert)
    if current_user.role == models.UserRole.customer:
        query = query.filter(models.Alert.user_id == current_user.user_id)
    return query.order_by(models.Alert.created_at.desc()).all()


@router.patch("/{alert_id}", response_model=schemas.AlertOut)
def update_alert_status(
    alert_id: str,
    payload: schemas.AlertStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role("analyst", "admin")),
):
    alert = db.query(models.Alert).filter(models.Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if payload.status not in [s.value for s in models.AlertStatus]:
        raise HTTPException(status_code=400, detail="Invalid status")
    alert.status = payload.status
    db.commit()
    db.refresh(alert)
    return alert
