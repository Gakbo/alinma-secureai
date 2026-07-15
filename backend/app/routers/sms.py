from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas, auth
from app.database import get_db
from app.ml.sms_classifier import classify_sms

router = APIRouter(prefix="/sms", tags=["SMS Phishing Detection"])


@router.post("/check", response_model=schemas.SMSCheckResponse)
def check_sms(
    payload: schemas.SMSCheckRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    result = classify_sms(payload.message)

    sms_log = models.SMSLog(
        user_id=current_user.user_id,
        message=payload.message,
        classification=result.classification,
        risk_score=result.risk_score,
        explanation=result.explanation,
    )
    db.add(sms_log)

    # Auto-generate a fraud alert for high-risk messages.
    if result.classification == "fraud":
        alert = models.Alert(
            user_id=current_user.user_id,
            alert_type="sms_phishing",
            severity=models.RiskLevel.high,
            description=f"Fraud SMS detected (score {result.risk_score}): {result.explanation}",
        )
        db.add(alert)
        # Bump the user's scam exposure score.
        current_user.scam_exposure_score = min(current_user.scam_exposure_score + 10, 100)
        db.add(current_user)

    db.commit()
    db.refresh(sms_log)

    return schemas.SMSCheckResponse(
        sms_id=sms_log.sms_id,
        classification=result.classification,
        risk_score=result.risk_score,
        explanation=result.explanation,
        suspicious_keywords=result.suspicious_keywords,
        contains_suspicious_url=result.contains_suspicious_url,
    )
