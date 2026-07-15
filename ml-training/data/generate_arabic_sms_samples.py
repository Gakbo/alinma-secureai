"""
Generates a labeled Arabic + English banking SMS dataset to supplement the
English-only SMS Spam Collection dataset (addresses the "limited Arabic
phishing datasets" challenge noted in your Data Sources slide).

Uses template + slot-filling to produce realistic variation while staying
labeled and small enough to hand-review before training. Real logged phishing
SMS reported by users (with personal details removed) will always generalize
better than templates alone -- add those to data/arabic_sms_manual.csv if
your team collects any during the hackathon.

Run:
    python generate_arabic_sms_samples.py

Output:
    data/arabic_english_sms_samples.csv  (columns: message, label)
    label is one of: safe, phishing
"""
import random
import pandas as pd

random.seed(42)

BANK_NAMES = ["الإنماء", "Alinma"]
AMOUNTS = ["500", "1,200", "5,000", "10,000", "25,000"]
LINKS = ["bit.ly/verify-acc", "alinma-secure.xyz", "alinma-update.top", "secure-alinma.info"]

# Phishing templates (Arabic) -- generic urgency/impersonation patterns
# commonly reported in banking phishing, used here only to train a
# defensive classifier.
PHISHING_TEMPLATES_AR = [
    "عزيزي عميل بنك {bank}، حسابك سيتم إيقافه اليوم. يرجى التحقق فورًا عبر الرابط: {link}",
    "تنبيه: تم رصد نشاط غير معتاد على حسابك في بنك {bank}. حدّث بياناتك الآن: {link}",
    "مبروك! ربحت {amount} ريال من بنك {bank}. اضغط هنا للمطالبة: {link}",
    "بنك {bank}: سيتم حظر بطاقتك خلال 24 ساعة ما لم تؤكد هويتك عبر: {link}",
    "رسالة عاجلة من {bank}: يوجد تحويل مشبوه بقيمة {amount} ريال، أوقفه الآن من هنا: {link}",
]

# Safe / legitimate-style Arabic banking messages
SAFE_TEMPLATES_AR = [
    "رمز التحقق الخاص بك من بنك {bank} هو {otp}. لا تشاركه مع أحد.",
    "تم تحويل {amount} ريال من حسابك بنجاح في {bank}. الرقم المرجعي {otp}.",
    "تذكير: موعد سداد بطاقتك الائتمانية لدى {bank} خلال {days} أيام.",
    "شكرًا لتعاملكم مع {bank}. رصيدكم الحالي متاح عبر التطبيق الرسمي، رقم الطلب {otp}.",
    "تنبيه: تسجيل دخول جديد إلى حسابك في {bank} من جهاز معروف بتاريخ اليوم.",
]

PHISHING_TEMPLATES_EN = [
    "Dear {bank} customer, your account will be suspended today. Verify immediately: {link}",
    "Unusual activity detected on your {bank} account. Update your info now: {link}",
    "Congratulations! You won SAR {amount} from {bank}. Claim here: {link}",
    "{bank} Alert: your card will be blocked in 24h unless you confirm your identity: {link}",
    "Urgent {bank} notice: suspicious transfer of SAR {amount} detected, cancel here: {link}",
]

SAFE_TEMPLATES_EN = [
    "Your {bank} OTP is {otp}. Do not share it with anyone.",
    "SAR {amount} was successfully transferred from your {bank} account. Ref {otp}.",
    "Reminder: your {bank} credit card payment is due in {days} days.",
    "Thank you for banking with {bank}. Check your balance in the official app, request {otp}.",
    "Alert: a new login to your {bank} account was detected from a known device today.",
]


def fill(template: str) -> str:
    return template.format(
        bank=random.choice(BANK_NAMES),
        amount=random.choice(AMOUNTS),
        link=random.choice(LINKS),
        otp=random.randint(1000, 9999),
        days=random.randint(1, 7),
    )


def main(n_per_template: int = 40):
    rows = []
    for templates, label in [
        (PHISHING_TEMPLATES_AR, "phishing"),
        (PHISHING_TEMPLATES_EN, "phishing"),
        (SAFE_TEMPLATES_AR, "safe"),
        (SAFE_TEMPLATES_EN, "safe"),
    ]:
        for t in templates:
            for _ in range(n_per_template):
                rows.append({"message": fill(t), "label": label})

    df = pd.DataFrame(rows).drop_duplicates(subset="message").sample(frac=1, random_state=42).reset_index(drop=True)
    df.to_csv("data/arabic_english_sms_samples.csv", index=False)

    print(f"Generated {len(df)} labeled SMS samples")
    print(df["label"].value_counts())
    print("Saved to data/arabic_english_sms_samples.csv")
    print("\nNOTE: these are TEMPLATE-based synthetic examples for training diversity.")
    print("For a stronger model, supplement with real anonymized phishing reports")
    print("your team collects, added to data/arabic_sms_manual.csv (same 2 columns).")


if __name__ == "__main__":
    main()
