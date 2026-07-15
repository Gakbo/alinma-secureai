"""
Populates the database with demo users, an analyst account, and sample
alerts so the dashboard isn't empty for your presentation.

Run with:
    python seed_data.py
"""
from app.database import SessionLocal, Base, engine
from app import models, auth

Base.metadata.create_all(bind=engine)
db = SessionLocal()

demo_accounts = [
    {"name": "Sara Al-Qahtani", "email": "sara.customer@example.com", "role": "customer", "password": "Password123"},
    {"name": "Fahad Al-Otaibi", "email": "fahad.customer@example.com", "role": "customer", "password": "Password123"},
    {"name": "Fraud Analyst", "email": "analyst@alinma.com", "role": "analyst", "password": "Password123"},
]

created_users = {}
for acc in demo_accounts:
    existing = db.query(models.User).filter(models.User.email == acc["email"]).first()
    if existing:
        created_users[acc["email"]] = existing
        continue
    user = models.User(
        name=acc["name"],
        email=acc["email"],
        hashed_password=auth.hash_password(acc["password"]),
        role=acc["role"],
        risk_score=72 if acc["role"] == "customer" and "Fahad" in acc["name"] else 20,
    )
    db.add(user)
    db.flush()
    created_users[acc["email"]] = user

db.commit()

# Sample alert for the high-risk demo customer.
fahad = created_users["fahad.customer@example.com"]
existing_alert = db.query(models.Alert).filter(models.Alert.user_id == fahad.user_id).first()
if not existing_alert:
    alert = models.Alert(
        user_id=fahad.user_id,
        alert_type="transaction",
        severity=models.RiskLevel.high,
        description="High-risk transaction of SAR 25,000 to a new foreign recipient.",
    )
    db.add(alert)
    db.commit()

db.close()

print("Seed data created. Demo login credentials:")
for acc in demo_accounts:
    print(f"  {acc['role']:10s} -> email: {acc['email']:30s} password: {acc['password']}")
