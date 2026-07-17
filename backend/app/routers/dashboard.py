from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas, auth
from app.database import get_db

router = APIRouter(prefix="/dashboard", tags=["Analyst Dashboard"])


@router.get("/summary", response_model=schemas.DashboardSummary)
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role("analyst", "admin")),
):
    total_alerts = db.query(models.Alert).count()
    open_alerts = db.query(models.Alert).filter(
        models.Alert.status == models.AlertStatus.open
    ).count()
    high_risk_users = db.query(models.User).filter(models.User.risk_score >= 70).count()

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    fraud_attempts_today = db.query(models.SMSLog).filter(
        models.SMSLog.classification == models.SMSClassification.fraud,
        models.SMSLog.created_at >= today_start,
    ).count()

    total_transactions_checked = db.query(models.Transaction).count()
    avg_risk = db.query(func.avg(models.Transaction.risk_score)).scalar() or 0.0

    return schemas.DashboardSummary(
        total_alerts=total_alerts,
        open_alerts=open_alerts,
        high_risk_users=high_risk_users,
        fraud_attempts_today=fraud_attempts_today,
        total_transactions_checked=total_transactions_checked,
        average_transaction_risk=round(avg_risk, 3),
    )


@router.get("/high-risk-users")
def high_risk_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role("analyst", "admin")),
):
    users = db.query(models.User).filter(models.User.risk_score >= 50).order_by(
        models.User.risk_score.desc()
    ).all()
    return [
        {
            "user_id": u.user_id,
            "name": u.name,
            "risk_score": u.risk_score,
            "scam_exposure_score": u.scam_exposure_score,
            "device_trust_score": u.device_trust_score,
        }
        for u in users
    ]


@router.get("/recent-alerts")
def recent_alerts(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role("analyst", "admin")),
):
    alerts = db.query(models.Alert).order_by(models.Alert.created_at.desc()).limit(limit).all()
    return alerts


@router.get("/fraud-trend")
def fraud_trend(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role("analyst", "admin")),
):
    """Daily alert counts for the last 7 days (for line chart)."""
    result = []
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    for i in range(6, -1, -1):
        day_start = today - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        count = db.query(models.Alert).filter(
            models.Alert.created_at >= day_start,
            models.Alert.created_at < day_end,
        ).count()
        result.append({"date": day_start.strftime("%b %d"), "count": count})
    return result


@router.get("/region-stats")
def region_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role("analyst", "admin")),
):
    """Fraud alert counts by Saudi Arabia region (stored in alert description prefix)."""
    regions = ["Riyadh", "Jeddah", "Dammam", "Mecca", "Medina", "Abha", "Tabuk"]
    result = []
    for region in regions:
        count = db.query(models.Alert).filter(
            models.Alert.description.ilike(f"[{region}]%")
        ).count()
        result.append({"region": region, "count": count})
    return result
