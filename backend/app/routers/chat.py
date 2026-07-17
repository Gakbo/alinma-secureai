"""
Alinma SecureAI — AI Banking Assistant
POST /chat/message  →  { reply: str }

Primary: OpenAI gpt-4o-mini (max_retries=0 so quota failures fall back instantly).
Fallback: rule-based keyword responder in both English and Arabic with a numbered
          IVR-style menu (type 1-7 to jump to a topic, 0 to return to menu).
"""
import os
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.models import User
from app.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["AI Assistant"])

# ---------------------------------------------------------------------------
# System prompts (OpenAI path)
# ---------------------------------------------------------------------------
_SYSTEM_EN = """You are the Alinma SecureAI Assistant — a helpful, professional, \
and friendly AI banking guide available 24/7 to Alinma Bank customers.

Help customers with: fraud alerts, Transfer Guardian risk scores, phishing SMS \
detection, account security, password reset, and Security Score interpretation.

Rules:
- Be concise (≤150 words unless detail is needed)
- For account actions (balance, freeze card, dispute) direct to 920001000 or a branch
- Never ask for passwords, card numbers, or OTPs
- Decline off-topic questions politely
- Respond in English
- End EVERY reply (except greetings) with exactly this line on its own:
  ↩️ Type **0** to return to the main menu.

Alinma facts: Contact 920001000 (24/7). Real SMS never contain links. \
Risk score: 0–34 low, 35–69 medium, 70+ high.

Menu topics (for reference):
1 Transfer Guardian  2 SMS Phishing  3 Fraud Alerts  4 Security Score
5 Password Reset     6 OTP Safety    7 Contact Alinma"""

_SYSTEM_AR = """أنت مساعد Alinma SecureAI — مساعد مصرفي ذكي ومهني ومتاح 24/7 لعملاء مصرف الإنماء.

ساعد العملاء في: تنبيهات الاحتيال، درجات مخاطر مراقب التحويلات، كشف رسائل التصيد، \
أمان الحساب، إعادة تعيين كلمة المرور، وتفسير درجة الأمان.

القواعد:
- كن موجزاً (≤150 كلمة ما لم تكن التفاصيل ضرورية)
- للإجراءات المتعلقة بالحساب (الرصيد، تجميد البطاقة، الاعتراض) أحِل إلى 920001000 أو فرع
- لا تطلب كلمات المرور أو أرقام البطاقات أو رموز OTP
- ارفض الأسئلة خارج النطاق بلطف
- أجب باللغة العربية دائماً
- اختم كل رد (عدا التحيات) بهذا السطر تماماً:
  ↩️ اكتب **0** للعودة إلى القائمة الرئيسية.

معلومات الإنماء: التواصل على 920001000 (24/7). الرسائل الحقيقية لا تحتوي روابط أبداً. \
درجة المخاطر: 0–34 منخفضة، 35–69 متوسطة، 70+ مرتفعة.

موضوعات القائمة (للمرجع):
1 مراقب التحويلات  2 التصيد  3 تنبيهات الاحتيال  4 درجة الأمان
5 كلمة المرور      6 OTP    7 التواصل مع الإنماء"""

# ---------------------------------------------------------------------------
# Menu constants
# ---------------------------------------------------------------------------
_MENU_EN = (
    "Hello! 😊 How can I help you today? Reply with a number or just ask your question:\n\n"
    "1️⃣  Transfer Guardian — understand your risk score\n"
    "2️⃣  SMS Phishing — spot fake messages\n"
    "3️⃣  Fraud Alerts — what they mean & what to do\n"
    "4️⃣  Security Score — your account risk level\n"
    "5️⃣  Password Reset — recover your account\n"
    "6️⃣  OTP Safety — protect your one-time codes\n"
    "7️⃣  Contact Alinma — phone & branch info\n\n"
    "Type **0** or \"menu\" to return here anytime."
)

_MENU_AR = (
    "أهلاً! 😊 كيف يمكنني مساعدتك؟ أرسل رقماً أو اكتب سؤالك مباشرةً:\n\n"
    "1️⃣  مراقب التحويلات — افهم درجة مخاطرك\n"
    "2️⃣  التصيد عبر SMS — اكشف الرسائل المزيفة\n"
    "3️⃣  تنبيهات الاحتيال — ماذا تعني وماذا تفعل\n"
    "4️⃣  درجة الأمان — مستوى مخاطر حسابك\n"
    "5️⃣  إعادة تعيين كلمة المرور — استعد حسابك\n"
    "6️⃣  حماية OTP — آمن رمزك الأحادي\n"
    "7️⃣  التواصل مع الإنماء — الهاتف والفروع\n\n"
    "اكتب **0** أو \"القائمة\" للعودة هنا في أي وقت."
)

_FOOTER_EN = "\n\n↩️ Type **0** to return to the main menu."
_FOOTER_AR = "\n\n↩️ اكتب **0** للعودة إلى القائمة الرئيسية."

# ---------------------------------------------------------------------------
# Rule-based fallback — English and Arabic entries
# Each tuple: (en_keywords, ar_keywords, en_reply, ar_reply)
# Order matters — _NUMBER_MAP references these by index.
# ---------------------------------------------------------------------------
_RULES = [
    # 0 → menu option 1
    (
        ["transfer guardian", "transfer risk", "risk score", "score transfer",
         "transaction score", "how is transfer", "transfer safe"],
        ["مراقب التحويلات", "درجة المخاطر", "فحص التحويل", "تحويل آمن",
         "خطر التحويل", "تقييم التحويل"],
        "Transfer Guardian scores your transactions 0–100 for fraud risk.\n\n"
        "• **Low (0–34)** → safe to proceed\n"
        "• **Medium (35–69)** → verify before sending\n"
        "• **High (70+)** → reject and contact us\n\n"
        "Key factors: amount vs. your typical spending, new recipient, destination country, "
        "and your device trust score.",
        "يقيّم مراقب التحويلات معاملاتك من 0 إلى 100 لكشف مخاطر الاحتيال.\n\n"
        "• **منخفضة (0–34)** ← آمن للمتابعة\n"
        "• **متوسطة (35–69)** ← تحقق قبل الإرسال\n"
        "• **مرتفعة (70+)** ← ارفض وتواصل معنا\n\n"
        "العوامل الرئيسية: المبلغ مقارنةً بعاداتك، المستفيد الجديد، الدولة المستقبِلة، "
        "ومستوى الثقة بجهازك.",
    ),
    # 1 → menu option 2
    (
        ["phishing", "fake sms", "suspicious sms", "fake message", "spam sms",
         "identify fake", "real sms", "alinma sms", "how to spot"],
        ["تصيد", "رسالة مزيفة", "رسالة مشبوهة", "احتيال رسالة", "رابط مشبوه",
         "sms مزيف", "رسالة كاذبة", "رسالة وهمية", "كيف أميز"],
        "Real Alinma SMS messages **never contain links** and never ask you to click anything. "
        "They only confirm what already happened.\n\n"
        "If an SMS has a link or says your account is 'suspended' — that is phishing. "
        "Paste the message into the **SMS Scanner** in this app for an instant AI verdict.",
        "رسائل مصرف الإنماء الحقيقية **لا تحتوي أبداً على روابط** ولا تطلب منك النقر على أي شيء. "
        "تؤكد فقط ما حدث بالفعل.\n\n"
        "إذا احتوت الرسالة على رابط أو طلبت 'التحقق' من حسابك — فهي **احتيال**. "
        "الصق الرسالة في **فاحص الرسائل** في هذا التطبيق للحصول على تحليل فوري.",
    ),
    # 2 → menu option 3
    (
        ["fraud alert", "alert mean", "what is alert", "got alert", "why alert",
         "fraud detected", "my alert"],
        ["تنبيه احتيال", "تنبيه", "تحذير احتيال", "نشاط مشبوه", "ماذا يعني التنبيه",
         "رسالة تحذير", "إشعار احتيال"],
        "A fraud alert is raised automatically when a high-risk transaction (score ≥ 70) "
        "or suspicious SMS is detected. An analyst reviews every alert.\n\n"
        "Open **Fraud Alerts**, review the event, and acknowledge it. "
        "If you don't recognise the activity, call **920001000** immediately.",
        "يُرسَل تنبيه الاحتيال تلقائياً عند رصد معاملة عالية المخاطر (درجة ≥ 70) "
        "أو رسالة تصيد. يراجع كل تنبيه محلل متخصص.\n\n"
        "افتح **تنبيهات الاحتيال**، راجع الحدث، وأقر باستلامه. "
        "إذا لم تتعرف على النشاط، اتصل بـ **920001000** فوراً.",
    ),
    # 3 → menu option 4
    (
        ["security score", "my score", "what is my score", "risk profile", "account score"],
        ["درجة الأمان", "نقاط الأمان", "ملف المخاطر", "درجتي", "تقييم الأمان",
         "مستوى الأمان"],
        "Your Security Score (0–100) reflects your account's fraud risk profile.\n\n"
        "• **70–100** → low risk, normal activity\n"
        "• **40–69** → moderate — some unusual patterns\n"
        "• **0–39** → elevated risk — review your alerts\n\n"
        "Check the **Security Score** page for a full breakdown.",
        "تعكس درجة الأمان (0–100) مستوى مخاطر الاحتيال في حسابك.\n\n"
        "• **70–100** ← مخاطر منخفضة، نشاط طبيعي\n"
        "• **40–69** ← متوسط — بعض الأنماط غير المعتادة\n"
        "• **0–39** ← مخاطر مرتفعة — راجع تنبيهاتك الأخيرة\n\n"
        "افتح صفحة **درجة الأمان** للاطلاع على التفاصيل الكاملة.",
    ),
    # 4 → menu option 5
    (
        ["password", "reset password", "forgot password", "can't login",
         "locked out", "change password", "reset my"],
        ["كلمة المرور", "نسيت كلمة المرور", "تغيير كلمة المرور",
         "استعادة الحساب", "لا أستطيع تسجيل الدخول", "إعادة تعيين"],
        "To reset your password:\n"
        "1. Go to the login page\n"
        "2. Click **'Forgot your password?'**\n"
        "3. Enter your registered email\n"
        "4. Follow the reset link — expires in **1 hour**\n\n"
        "If you don't receive the email, check spam or call **920001000**.",
        "لإعادة تعيين كلمة المرور:\n"
        "1. اذهب إلى صفحة تسجيل الدخول\n"
        "2. انقر على **'نسيت كلمة المرور؟'**\n"
        "3. أدخل بريدك الإلكتروني المسجل\n"
        "4. اتبع رابط الاستعادة — صالح لمدة **ساعة واحدة**\n\n"
        "إذا لم تصلك الرسالة، تحقق من البريد المزعج أو اتصل بـ **920001000**.",
    ),
    # 5 → menu option 6
    (
        ["otp", "one time password", "verification code", "someone asked",
         "share otp", "give otp"],
        ["رمز التحقق", "OTP", "كلمة مرور لمرة واحدة", "شاركت الرمز",
         "أعطيت الرمز", "رمز التفعيل"],
        "**Never share your OTP with anyone** — not even someone claiming to be from Alinma. "
        "Alinma staff will never ask for your OTP, password, or card number.\n\n"
        "If you've already shared it, call **920001000** immediately.",
        "**لا تشارك رمز OTP مع أي شخص** — حتى من يدّعي أنه من الإنماء. "
        "لن يطلب موظفو الإنماء منك أبداً رمز OTP أو كلمة المرور أو رقم البطاقة.\n\n"
        "إذا شاركت الرمز بالفعل، اتصل بـ **920001000** فوراً لتأمين حسابك.",
    ),
    # 6 → menu option 7
    (
        ["contact", "phone number", "helpline", "support", "call alinma",
         "customer service", "reach alinma"],
        ["اتصال", "هاتف", "مركز الاتصال", "دعم", "خدمة العملاء",
         "رقم الإنماء", "التواصل مع الإنماء"],
        "**Alinma Contact Centre: 920001000** — available 24/7.\n\n"
        "You can also visit any Alinma branch. For fraud or security questions, "
        "use this app: SMS Scanner, Transfer Guardian, Fraud Alerts.",
        "**مركز اتصال الإنماء: 920001000** — متاح 24/7.\n\n"
        "يمكنك أيضاً زيارة أي فرع من فروع مصرف الإنماء. للأسئلة المتعلقة بالاحتيال والأمان، "
        "استخدم هذا التطبيق: فاحص الرسائل، مراقب التحويلات، تنبيهات الاحتيال.",
    ),
    # 7 — device trust (keyword only, not in menu)
    (
        ["device trust", "trusted device", "device score", "new device"],
        ["ثقة الجهاز", "جهاز موثوق", "درجة الجهاز", "جهاز جديد", "مستوى الجهاز"],
        "Your device trust score reflects how safely your device has been used. "
        "New devices start lower and improve with successful transfers. "
        "Low device trust raises your Transfer Guardian risk score.",
        "تعكس درجة ثقة الجهاز مدى سلامة استخدامه في المعاملات. "
        "تبدأ الأجهزة الجديدة بدرجة منخفضة وتتحسن مع المعاملات الناجحة. "
        "انخفاض ثقة الجهاز يرفع درجة مخاطر مراقب التحويلات.",
    ),
    # 8 — account actions (keyword only, not in menu)
    (
        ["account", "balance", "freeze", "card", "dispute", "block card",
         "transaction history", "statement"],
        ["رصيد", "حساب", "تجميد", "بطاقة", "اعتراض", "إيقاف البطاقة",
         "كشف حساب", "تاريخ المعاملات"],
        "For account actions — balance, freezing a card, disputing a transaction — "
        "contact Alinma directly:\n\n📞 **920001000** (24/7) or visit a branch.\n\n"
        "I can help with fraud prevention and security questions here in the app.",
        "للإجراءات المتعلقة بالحساب — الرصيد أو تجميد البطاقة أو الاعتراض — "
        "تواصل مع مصرف الإنماء مباشرةً:\n\n📞 **920001000** (متاح 24/7) أو زيارة أقرب فرع.\n\n"
        "يمكنني المساعدة في أسئلة الاحتيال والأمان هنا في التطبيق.",
    ),
    # 9 — greeting (keyword only; reply IS the menu)
    (
        ["hello", "hi", "hey", "help", "what can you do", "who are you",
         "how are you", "how r you", "good morning", "good evening", "good day",
         "good afternoon", "good night", "salam", "assalam", "alaikum",
         "ahlan", "marhaba", "greetings", "sup", "howdy"],
        ["مرحبا", "مرحباً", "السلام", "السلام عليكم", "وعليكم السلام",
         "أهلا", "أهلاً", "أهلين", "هلا", "هلو", "مساعدة", "من أنت",
         "ماذا تفعل", "كيف حالك", "كيف الحال", "ايش أخبارك", "كيف أنت",
         "صباح الخير", "مساء الخير", "تصبح على خير", "اهلا وسهلا"],
        # EN greeting → show menu (no footer; menu has its own return hint)
        _MENU_EN,
        # AR greeting → show menu
        _MENU_AR,
    ),
]

# Maps digit strings "1"–"7" to _RULES indices (menu order)
_NUMBER_MAP: dict[str, int] = {
    "1": 0,   # Transfer Guardian
    "2": 1,   # SMS Phishing
    "3": 2,   # Fraud Alerts
    "4": 3,   # Security Score
    "5": 4,   # Password Reset
    "6": 5,   # OTP Safety
    "7": 6,   # Contact Alinma
}

# Triggers that return the main menu
_MENU_TRIGGERS_EN = {"0", "menu", "main menu", "back", "start", "home"}
_MENU_TRIGGERS_AR = {"0", "القائمة", "القائمة الرئيسية", "رجوع", "رئيسية", "البداية"}


def _rule_reply(messages: list, lang: str = "en") -> str:
    """
    IVR-style rule engine:
      1. "0" / "menu" / Arabic equivalents → main menu
      2. digit "1"–"7" → jump to that topic + footer
      3. keyword match → topic reply + footer
      4. greeting keywords → menu (no extra footer)
      5. fallback generic → hint to type 0
    """
    last_user = next(
        (m.content for m in reversed(messages) if m.role == "user"), ""
    )
    stripped = last_user.strip()
    text = stripped.lower()
    ar = lang == "ar"

    menu = _MENU_AR if ar else _MENU_EN
    footer = _FOOTER_AR if ar else _FOOTER_EN

    # 1. Menu / back command
    triggers = _MENU_TRIGGERS_AR if ar else _MENU_TRIGGERS_EN
    if text in triggers or stripped in _MENU_TRIGGERS_AR or stripped in _MENU_TRIGGERS_EN:
        return menu

    # 2. Numbered shortcut (digits 1-7)
    if text in _NUMBER_MAP:
        idx = _NUMBER_MAP[text]
        reply = _RULES[idx][3] if ar else _RULES[idx][2]
        return reply + footer

    # 3 & 4. Keyword / greeting matching
    for en_kw, ar_kw, en_reply, ar_reply in _RULES:
        keywords = ar_kw if ar else en_kw
        if any(kw in text for kw in keywords):
            reply = ar_reply if ar else en_reply
            # Greeting rule reply IS the menu — no extra footer
            is_menu_reply = (reply == _MENU_EN or reply == _MENU_AR)
            return reply if is_menu_reply else reply + footer

    # 5. Generic fallback
    if ar:
        return (
            "أنا هنا للمساعدة في أسئلة الأمان المصرفي.\n\n"
            "اكتب رقماً من 1 إلى 7 للانتقال إلى موضوع مباشرةً، "
            "أو اكتب **0** لعرض القائمة الكاملة، أو اسأل سؤالك بالعربية."
        )
    return (
        "I'm here to help with fraud prevention and account security.\n\n"
        "Type a number **1–7** to jump to a topic, type **0** to see the full menu, "
        "or just ask your question in plain English."
    )


# ---------------------------------------------------------------------------
# OpenAI client (max_retries=0 — fail fast, fall back immediately)
# ---------------------------------------------------------------------------
def _try_openai(messages: list, lang: str = "en") -> str | None:
    """Returns AI reply string or None if OpenAI is unavailable/quota exceeded."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, max_retries=0)
        system = _SYSTEM_AR if lang == "ar" else _SYSTEM_EN
        openai_messages = [{"role": "system", "content": system}]
        for msg in messages[-20:]:
            if msg.role in ("user", "assistant"):
                openai_messages.append({"role": msg.role, "content": msg.content})
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=openai_messages,
            max_tokens=400,
            temperature=0.4,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("OpenAI unavailable (%s); using rule-based fallback.", exc)
        return None


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ChatMessage(BaseModel):
    role: str       # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    lang: Optional[str] = "en"   # "en" | "ar"


class ChatResponse(BaseModel):
    reply: str


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------
@router.post("/message", response_model=ChatResponse)
def chat_message(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Send a message to the Alinma AI banking assistant.
    Tries OpenAI first (no retries); falls back to the rule-based menu engine.
    Pass lang='ar' for Arabic replies.
    """
    if not body.messages:
        raise HTTPException(status_code=400, detail="No messages provided.")

    lang = body.lang if body.lang in ("en", "ar") else "en"
    ar = lang == "ar"
    footer = _FOOTER_AR if ar else _FOOTER_EN
    menu   = _MENU_AR   if ar else _MENU_EN

    # Determine whether the last user message is a deterministic command
    # (digit 1-7, "0", "menu", Arabic equivalents). These always bypass OpenAI
    # so navigation is instant and consistent regardless of API availability.
    last_user = next(
        (m.content for m in reversed(body.messages) if m.role == "user"), ""
    )
    text = last_user.strip().lower()
    is_deterministic = (
        text in _NUMBER_MAP
        or text in _MENU_TRIGGERS_EN
        or text in _MENU_TRIGGERS_AR
    )

    if is_deterministic:
        # Always use rule engine for numbered shortcuts and menu commands
        reply = _rule_reply(body.messages, lang)
    else:
        # Free-text: try OpenAI first, fall back to rule engine
        reply = _try_openai(body.messages, lang) or _rule_reply(body.messages, lang)
        # Ensure every non-menu reply carries the return-to-menu footer.
        # The rule engine already appends it; add it to OpenAI replies that lack it.
        is_menu_reply = reply.strip() == menu.strip()
        has_footer = reply.endswith(_FOOTER_EN.strip()) or reply.endswith(_FOOTER_AR.strip())
        if not is_menu_reply and not has_footer:
            reply = reply + footer

    return ChatResponse(reply=reply)
