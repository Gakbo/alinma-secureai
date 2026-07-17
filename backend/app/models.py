"""
SQLAlchemy ORM models — mirrors the DB design from the project spec:
Users, Transactions, SMS Logs, Alerts, Devices.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Float, Integer, DateTime, ForeignKey, Enum, Text, Boolean
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class UserRole(str, enum.Enum):
    customer = "customer"
    analyst = "analyst"
    admin = "admin"


class RiskLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class SMSClassification(str, enum.Enum):
    safe = "safe"
    suspicious = "suspicious"
    fraud = "fraud"


class AlertStatus(str, enum.Enum):
    open = "open"
    resolved = "resolved"


class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.customer, nullable=False)

    # Customer Security Score components
    risk_score = Column(Float, default=0.0)          # overall behavior risk (0-100)
    device_trust_score = Column(Float, default=100.0)  # 0-100, higher = more trusted
    scam_exposure_score = Column(Float, default=0.0)   # 0-100, higher = more exposed

    created_at = Column(DateTime, default=datetime.utcnow)
    # Incremented on every password reset so old JWTs are immediately rejected.
    password_version = Column(Integer, default=0, nullable=False)

    transactions = relationship("Transaction", back_populates="user")
    sms_logs = relationship("SMSLog", back_populates="user")
    alerts = relationship("Alert", back_populates="user")
    devices = relationship("Device", back_populates="user")


class Device(Base):
    __tablename__ = "devices"

    device_id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    ip_address = Column(String, nullable=True)
    device_type = Column(String, nullable=True)   # e.g. "mobile", "web"
    trust_score = Column(Float, default=100.0)
    last_seen = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="devices")


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    amount = Column(Float, nullable=False)
    recipient = Column(String, nullable=False)
    is_new_recipient = Column(Integer, default=0)   # 0/1 boolean flag
    country = Column(String, nullable=True)
    device_id = Column(String, ForeignKey("devices.device_id"), nullable=True)

    risk_score = Column(Float, nullable=True)        # 0-1 fraud probability
    risk_level = Column(Enum(RiskLevel), nullable=True)
    status = Column(String, default="pending")        # pending/approved/rejected/verify
    explanation = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="transactions")


class SMSLog(Base):
    __tablename__ = "sms_logs"

    sms_id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    message = Column(Text, nullable=False)
    classification = Column(Enum(SMSClassification), nullable=True)
    risk_score = Column(Float, nullable=True)        # 0-100
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="sms_logs")


class Alert(Base):
    __tablename__ = "alerts"

    alert_id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    alert_type = Column(String, nullable=False)       # "sms_phishing" / "transaction" / "login_anomaly"
    severity = Column(Enum(RiskLevel), default=RiskLevel.low)
    status = Column(Enum(AlertStatus), default=AlertStatus.open)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    acknowledged_by_customer = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="alerts")


class PasswordReset(Base):
    """Short-lived single-use tokens for the forgot-password flow."""
    __tablename__ = "password_resets"

    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String, nullable=False, index=True)
    token = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Integer, default=0)   # 0 = unused, 1 = used
    created_at = Column(DateTime, default=datetime.utcnow)
