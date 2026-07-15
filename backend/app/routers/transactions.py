from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas, auth
from app.database import get_db
from app.ml.transaction_risk import score_transaction

router = APIRouter(prefix="/transactions", tags=["Transaction Risk Analysis"])


@router.post("/check", response_model=schemas.TransactionResponse)
def check_transaction(
    payload: schemas.TransactionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    device_trust = 100.0
    if payload.device_id:
        device = db.query(models.Device).filter(
            models.Device.device_id == payload.device_id
        ).first()
        if device:
            device_trust = device.trust_score

    result = score_transaction(
        amount=payload.amount,
        is_new_recipient=payload.is_new_recipient,
        country=payload.country,
        device_trust_score=device_trust,
    )

    txn = models.Transaction(
        user_id=current_user.user_id,
        amount=payload.amount,
        recipient=payload.recipient,
        is_new_recipient=int(payload.is_new_recipient),
        country=payload.country,
        device_id=payload.device_id,
        risk_score=result.risk_score,
        risk_level=result.risk_level,
        status=result.recommended_action,
        explanation=result.explanation,
    )
    db.add(txn)

    if result.risk_level == "high":
        alert = models.Alert(
            user_id=current_user.user_id,
            alert_type="transaction",
            severity=models.RiskLevel.high,
            description=f"High-risk transaction of SAR {payload.amount}: {result.explanation}",
        )
        db.add(alert)

    db.commit()
    db.refresh(txn)

    return schemas.TransactionResponse(
        transaction_id=txn.transaction_id,
        risk_score=result.risk_score,
        risk_level=result.risk_level,
        recommended_action=result.recommended_action,
        explanation=result.explanation,
    )
