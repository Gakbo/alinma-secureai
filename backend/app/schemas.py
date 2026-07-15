"""
Pydantic schemas — request/response shapes for the API.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ---------- Auth / Users ----------

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(min_length=8)
    role: Optional[str] = "customer"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    user_id: str
    name: str
    email: EmailStr
    phone: Optional[str]
    role: str
    risk_score: float
    device_trust_score: float
    scam_exposure_score: float
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- SMS Phishing Detection ----------

class SMSCheckRequest(BaseModel):
    message: str = Field(min_length=1, description="Raw SMS text, Arabic or English")


class SMSCheckResponse(BaseModel):
    sms_id: str
    classification: str          # safe / suspicious / fraud
    risk_score: float            # 0-100
    explanation: str
    suspicious_keywords: list[str] = []
    contains_suspicious_url: bool = False


# ---------- Transaction Risk ----------

class TransactionRequest(BaseModel):
    amount: float
    recipient: str
    is_new_recipient: bool = False
    country: Optional[str] = "SA"
    device_id: Optional[str] = None


class TransactionResponse(BaseModel):
    transaction_id: str
    risk_score: float             # 0-1
    risk_level: str               # low / medium / high
    recommended_action: str       # approve / verify / reject
    explanation: str


# ---------- Alerts ----------

class AlertOut(BaseModel):
    alert_id: str
    user_id: str
    alert_type: str
    severity: str
    status: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AlertStatusUpdate(BaseModel):
    status: str   # "resolved" or "open"


# ---------- Dashboard ----------

class DashboardSummary(BaseModel):
    total_alerts: int
    open_alerts: int
    high_risk_users: int
    fraud_attempts_today: int
    total_transactions_checked: int
    average_transaction_risk: float
