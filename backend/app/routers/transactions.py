from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas, auth
from app.database import get_db
from app.ml.transaction_risk import score_transaction
from app.email_utils import send_fraud_alert_email

router = APIRouter(prefix="/transactions", tags=["Transaction Risk Analysis"])


@router.post("/check", response_model=schemas.TransactionResponse)
def check_transaction(
    payload: schemas.TransactionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    # Start from the customer's stored device-trust profile. The old default
    # of 100.0 ("fully trusted") masked genuinely risky transfers whenever the
    # client didn't send a device_id — device trust is one of the model's two
    # strongest features.
    device_trust = (
        current_user.device_trust_score
        if current_user.device_trust_score is not None else 100.0
    )
    if payload.device_id:
        device = db.query(models.Device).filter(
            models.Device.device_id == payload.device_id
        ).first()
        if device:
            device_trust = device.trust_score

    # Real transaction history depth for this customer (model feature).
    prior_count = (
        db.query(models.Transaction)
        .filter(models.Transaction.user_id == current_user.user_id)
        .count()
    )

    result = score_transaction(
        amount=payload.amount,
        is_new_recipient=payload.is_new_recipient,
        country=payload.country,
        device_trust_score=device_trust,
        prior_transaction_count=prior_count,
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

    high_risk_txn = result.risk_level == "high"
    if high_risk_txn:
        alert = models.Alert(
            user_id=current_user.user_id,
            alert_type="transaction",
            severity=models.RiskLevel.high,
            description=f"High-risk transaction of SAR {payload.amount}: {result.explanation}",
        )
        db.add(alert)

    db.commit()
    db.refresh(txn)

    if high_risk_txn:
        try:
            send_fraud_alert_email(
                to_email=current_user.email,
                customer_name=current_user.name,
                alert_type="transaction",
                severity="high",
            )
        except Exception:
            pass  # Email failure must not break the API response

    return schemas.TransactionResponse(
        transaction_id=txn.transaction_id,
        risk_score=result.risk_score,
        risk_level=result.risk_level,
        recommended_action=result.recommended_action,
        explanation=result.explanation,
    )
