"""
Rich demo seed data for Alinma SecureAI.
Drops and recreates all tables so every demo run starts clean.

Run with:
    cd backend && python seed_data.py
"""
from datetime import datetime, timedelta
from app.database import SessionLocal, Base, engine
from app import models, auth

# --- Reset ---------------------------------------------------------------
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
db = SessionLocal()

now = datetime.utcnow()

# --- Users ---------------------------------------------------------------
users_data = [
    {
        "name": "Sara Al-Qahtani",
        "email": "sara.customer@example.com",
        "password": "Password123",
        "role": "customer",
        "risk_score": 85.0,
        "device_trust_score": 40.0,
        "scam_exposure_score": 75.0,
    },
    {
        "name": "Fahad Al-Otaibi",
        "email": "fahad.customer@example.com",
        "password": "Password123",
        "role": "customer",
        "risk_score": 72.0,
        "device_trust_score": 55.0,
        "scam_exposure_score": 60.0,
    },
    {
        "name": "Mohammed Al-Ghamdi",
        "email": "mohammed.customer@example.com",
        "password": "Password123",
        "role": "customer",
        "risk_score": 45.0,
        "device_trust_score": 80.0,
        "scam_exposure_score": 30.0,
    },
    {
        "name": "Noura Al-Rashidi",
        "email": "noura.customer@example.com",
        "password": "Password123",
        "role": "customer",
        "risk_score": 12.0,
        "device_trust_score": 96.0,
        "scam_exposure_score": 8.0,
    },
    {
        "name": "Khalid Al-Shammari",
        "email": "khalid.customer@example.com",
        "password": "Password123",
        "role": "customer",
        "risk_score": 91.0,
        "device_trust_score": 22.0,
        "scam_exposure_score": 88.0,
    },
    {
        "name": "Fraud Analyst",
        "email": "analyst@alinma.com",
        "password": "Password123",
        "role": "analyst",
        "risk_score": 0.0,
        "device_trust_score": 100.0,
        "scam_exposure_score": 0.0,
    },
    {
        "name": "System Admin",
        "email": "admin@alinma.com",
        "password": "Password123",
        "role": "admin",
        "risk_score": 0.0,
        "device_trust_score": 100.0,
        "scam_exposure_score": 0.0,
    },
]

created_users = {}
for ud in users_data:
    u = models.User(
        name=ud["name"],
        email=ud["email"],
        hashed_password=auth.hash_password(ud["password"]),
        role=ud["role"],
        risk_score=ud["risk_score"],
        device_trust_score=ud["device_trust_score"],
        scam_exposure_score=ud["scam_exposure_score"],
    )
    db.add(u)
    db.flush()
    created_users[ud["email"]] = u

db.commit()

sara    = created_users["sara.customer@example.com"]
fahad   = created_users["fahad.customer@example.com"]
mohammed = created_users["mohammed.customer@example.com"]
noura   = created_users["noura.customer@example.com"]
khalid  = created_users["khalid.customer@example.com"]

# --- SMS Logs ------------------------------------------------------------
sms_logs = [
    {
        "user": sara,
        "message": "عزيزي عميل إنماء، سيتم إيقاف حسابك. يرجى النقر فوراً: http://alinma-verify.xyz",
        "classification": models.SMSClassification.fraud,
        "risk_score": 96.0,
        "explanation": "Impersonates Alinma Bank and contains an unrecognized link demanding immediate action.",
        "days_ago": 0,
    },
    {
        "user": fahad,
        "message": "Dear Alinma customer, your account will be suspended. Click here: http://secure-alinma.net/verify",
        "classification": models.SMSClassification.fraud,
        "risk_score": 91.0,
        "explanation": "Phishing attempt: fake urgency, unrecognized domain impersonating Alinma Bank.",
        "days_ago": 1,
    },
    {
        "user": khalid,
        "message": "إنماء: تم تسجيل دخول مشبوه من جهاز غير معروف. تحقق من حسابك.",
        "classification": models.SMSClassification.suspicious,
        "risk_score": 55.0,
        "explanation": "Mentions suspicious login and unknown device; no link present, but tone is alarming.",
        "days_ago": 2,
    },
    {
        "user": mohammed,
        "message": "Your Alinma transfer of SAR 500 to Mohammed A. was successful. Ref: TXN-20240715.",
        "classification": models.SMSClassification.safe,
        "risk_score": 4.0,
        "explanation": "Standard transaction confirmation. No suspicious links or urgency language detected.",
        "days_ago": 3,
    },
    {
        "user": sara,
        "message": "تهانينا! لقد فزت بجائزة مصرف إنماء. أدخل بياناتك البنكية هنا: http://win.alinma-prize.com",
        "classification": models.SMSClassification.fraud,
        "risk_score": 98.0,
        "explanation": "Classic prize scam. Requests banking credentials via a fraudulent website.",
        "days_ago": 4,
    },
]

for s in sms_logs:
    log = models.SMSLog(
        user_id=s["user"].user_id,
        message=s["message"],
        classification=s["classification"],
        risk_score=s["risk_score"],
        explanation=s["explanation"],
        created_at=now - timedelta(days=s["days_ago"], hours=2),
    )
    db.add(log)

# --- Transactions --------------------------------------------------------
transactions = [
    {
        "user": khalid,
        "amount": 28000.0,
        "recipient": "Unknown Holdings LLC",
        "is_new_recipient": 1,
        "country": "NG",
        "risk_score": 0.94,
        "risk_level": models.RiskLevel.high,
        "status": "rejected",
        "explanation": "Extremely high amount to a first-time foreign recipient in a high-risk jurisdiction.",
        "days_ago": 0,
    },
    {
        "user": sara,
        "amount": 15500.0,
        "recipient": "FastPay Services",
        "is_new_recipient": 1,
        "country": "PK",
        "risk_score": 0.82,
        "risk_level": models.RiskLevel.high,
        "status": "verify",
        "explanation": "Large transfer to a new recipient abroad. Initiated from an unrecognized device.",
        "days_ago": 1,
    },
    {
        "user": fahad,
        "amount": 3200.0,
        "recipient": "Ali Hassan",
        "is_new_recipient": 0,
        "country": "SA",
        "risk_score": 0.38,
        "risk_level": models.RiskLevel.medium,
        "status": "verify",
        "explanation": "Slightly above average amount for this account. Recipient is known.",
        "days_ago": 2,
    },
    {
        "user": mohammed,
        "amount": 1200.0,
        "recipient": "Huda Al-Ansari",
        "is_new_recipient": 0,
        "country": "SA",
        "risk_score": 0.12,
        "risk_level": models.RiskLevel.low,
        "status": "approved",
        "explanation": "Routine domestic transfer. Amount and recipient match historical patterns.",
        "days_ago": 3,
    },
    {
        "user": noura,
        "amount": 500.0,
        "recipient": "Jarir Bookstore",
        "is_new_recipient": 0,
        "country": "SA",
        "risk_score": 0.05,
        "risk_level": models.RiskLevel.low,
        "status": "approved",
        "explanation": "Small domestic payment to a known merchant.",
        "days_ago": 5,
    },
]

for t in transactions:
    txn = models.Transaction(
        user_id=t["user"].user_id,
        amount=t["amount"],
        recipient=t["recipient"],
        is_new_recipient=t["is_new_recipient"],
        country=t["country"],
        risk_score=t["risk_score"],
        risk_level=t["risk_level"],
        status=t["status"],
        explanation=t["explanation"],
        created_at=now - timedelta(days=t["days_ago"], hours=1),
    )
    db.add(txn)

# --- Alerts (spread over 7 days, with Saudi regions) ---------------------
alerts_data = [
    # Today (day 0)
    {
        "user": khalid,
        "alert_type": "suspicious_transaction",
        "severity": models.RiskLevel.high,
        "status": models.AlertStatus.open,
        "description": "[Riyadh] High-risk transfer of SAR 28,000 to unknown foreign entity in Nigeria. Transfer blocked automatically.",
        "days_ago": 0, "hours_ago": 1,
    },
    {
        "user": sara,
        "alert_type": "sms_phishing",
        "severity": models.RiskLevel.high,
        "status": models.AlertStatus.open,
        "description": "[Jeddah] Phishing SMS intercepted targeting Sara's account. Fake Alinma domain detected: alinma-prize.com.",
        "days_ago": 0, "hours_ago": 3,
    },
    {
        "user": fahad,
        "alert_type": "behavior_anomaly",
        "severity": models.RiskLevel.medium,
        "status": models.AlertStatus.open,
        "description": "[Riyadh] Unusual login pattern detected: 4 login attempts from 3 different IPs within 30 minutes.",
        "days_ago": 0, "hours_ago": 5,
    },
    # Day 1
    {
        "user": sara,
        "alert_type": "suspicious_transaction",
        "severity": models.RiskLevel.high,
        "status": models.AlertStatus.open,
        "description": "[Jeddah] Transfer of SAR 15,500 to new recipient abroad flagged for manual review.",
        "days_ago": 1, "hours_ago": 2,
    },
    {
        "user": khalid,
        "alert_type": "sms_phishing",
        "severity": models.RiskLevel.high,
        "status": models.AlertStatus.resolved,
        "description": "[Dammam] Phishing SMS detected: fake Alinma suspension notice with malicious link.",
        "days_ago": 1, "hours_ago": 8,
    },
    # Day 2
    {
        "user": fahad,
        "alert_type": "sms_phishing",
        "severity": models.RiskLevel.high,
        "status": models.AlertStatus.resolved,
        "description": "[Mecca] Phishing SMS impersonating Alinma Bank. User warned before clicking link.",
        "days_ago": 2, "hours_ago": 4,
    },
    {
        "user": mohammed,
        "alert_type": "login_anomaly",
        "severity": models.RiskLevel.medium,
        "status": models.AlertStatus.resolved,
        "description": "[Riyadh] Login from unrecognized device (iPhone 12, new IP). OTP verification sent.",
        "days_ago": 2, "hours_ago": 10,
    },
    {
        "user": khalid,
        "alert_type": "account_takeover",
        "severity": models.RiskLevel.high,
        "status": models.AlertStatus.open,
        "description": "[Dammam] Multiple failed password attempts followed by successful login from new device. Account flagged.",
        "days_ago": 2, "hours_ago": 14,
    },
    # Day 3
    {
        "user": sara,
        "alert_type": "behavior_anomaly",
        "severity": models.RiskLevel.medium,
        "status": models.AlertStatus.resolved,
        "description": "[Medina] Sudden increase in transaction frequency: 6 transactions in 2 hours vs. 2/week baseline.",
        "days_ago": 3, "hours_ago": 6,
    },
    {
        "user": noura,
        "alert_type": "sms_phishing",
        "severity": models.RiskLevel.low,
        "status": models.AlertStatus.resolved,
        "description": "[Jeddah] Suspicious SMS detected but classified as low confidence. User notified.",
        "days_ago": 3, "hours_ago": 11,
    },
    # Day 4
    {
        "user": khalid,
        "alert_type": "suspicious_transaction",
        "severity": models.RiskLevel.high,
        "status": models.AlertStatus.resolved,
        "description": "[Abha] Transaction of SAR 8,000 to first-time recipient in high-risk corridor. Verified by customer.",
        "days_ago": 4, "hours_ago": 3,
    },
    {
        "user": fahad,
        "alert_type": "login_anomaly",
        "severity": models.RiskLevel.medium,
        "status": models.AlertStatus.resolved,
        "description": "[Riyadh] Login at 03:15 AM from unrecognized browser. Unusual for this customer profile.",
        "days_ago": 4, "hours_ago": 9,
    },
    # Day 5
    {
        "user": sara,
        "alert_type": "sms_phishing",
        "severity": models.RiskLevel.high,
        "status": models.AlertStatus.resolved,
        "description": "[Tabuk] High-confidence phishing SMS: Arabic-language Alinma impersonation with credential harvesting link.",
        "days_ago": 5, "hours_ago": 5,
    },
    {
        "user": mohammed,
        "alert_type": "behavior_anomaly",
        "severity": models.RiskLevel.low,
        "status": models.AlertStatus.resolved,
        "description": "[Riyadh] Minor behavioral deviation: login from new browser on known device. No further action.",
        "days_ago": 5, "hours_ago": 12,
    },
    # Day 6
    {
        "user": khalid,
        "alert_type": "account_takeover",
        "severity": models.RiskLevel.high,
        "status": models.AlertStatus.resolved,
        "description": "[Dammam] Credential stuffing attempt: 12 failed logins from automated tool. IP blocked.",
        "days_ago": 6, "hours_ago": 7,
    },
]

for ad in alerts_data:
    alert = models.Alert(
        user_id=ad["user"].user_id,
        alert_type=ad["alert_type"],
        severity=ad["severity"],
        status=ad["status"],
        description=ad["description"],
        created_at=now - timedelta(days=ad["days_ago"], hours=ad["hours_ago"]),
    )
    db.add(alert)

db.commit()
db.close()

# Plain ASCII output: Windows consoles often use legacy codepages (cp1256 etc.)
# that cannot encode emoji, and a seed script must never crash on its summary.
print("Demo database seeded successfully!\n")
print("Demo login credentials:")
creds = [
    ("customer",  "sara.customer@example.com",     "Password123", "High risk - Jeddah"),
    ("customer",  "fahad.customer@example.com",    "Password123", "High risk - Riyadh"),
    ("customer",  "mohammed.customer@example.com", "Password123", "Medium risk - Riyadh"),
    ("customer",  "noura.customer@example.com",    "Password123", "Low risk - Jeddah"),
    ("customer",  "khalid.customer@example.com",   "Password123", "Very high risk - Dammam"),
    ("analyst",   "analyst@alinma.com",            "Password123", "Full dashboard access"),
    ("admin",     "admin@alinma.com",              "Password123", "Admin panel access"),
]
for role, email, pw, note in creds:
    print(f"  [{role:8s}] {email:38s} {pw}   ({note})")
