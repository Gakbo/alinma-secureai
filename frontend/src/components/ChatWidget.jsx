import { useState, useRef, useEffect } from "react";
import { sendChatMessage } from "../api.js";
import { useLanguage } from "../context/LanguageContext.jsx";

// ---------------------------------------------------------------------------
// Localisation strings
// ---------------------------------------------------------------------------
const MENU_EN =
  "Hello! 😊 How can I help you today? Reply with a number or just ask your question:\n\n" +
  "1️⃣  Transfer Guardian — understand your risk score\n" +
  "2️⃣  SMS Phishing — spot fake messages\n" +
  "3️⃣  Fraud Alerts — what they mean & what to do\n" +
  "4️⃣  Security Score — your account risk level\n" +
  "5️⃣  Password Reset — recover your account\n" +
  "6️⃣  OTP Safety — protect your one-time codes\n" +
  "7️⃣  Contact Alinma — phone & branch info\n\n" +
  'Type 0 or "menu" to return here anytime.';

const MENU_AR =
  "أهلاً! 😊 كيف يمكنني مساعدتك؟ أرسل رقماً أو اكتب سؤالك مباشرةً:\n\n" +
  "1️⃣  مراقب التحويلات — افهم درجة مخاطرك\n" +
  "2️⃣  التصيد عبر SMS — اكشف الرسائل المزيفة\n" +
  "3️⃣  تنبيهات الاحتيال — ماذا تعني وماذا تفعل\n" +
  "4️⃣  درجة الأمان — مستوى مخاطر حسابك\n" +
  "5️⃣  إعادة تعيين كلمة المرور — استعد حسابك\n" +
  "6️⃣  حماية OTP — آمن رمزك الأحادي\n" +
  "7️⃣  التواصل مع الإنماء — الهاتف والفروع\n\n" +
  'اكتب 0 أو "القائمة" للعودة هنا في أي وقت.';

const STR = {
  en: {
    title:       "SecureAI Assistant",
    subtitle:    "Available 24/7 · Alinma Bank",
    placeholder: "Type a number (1–7) or ask a question…",
    ariaOpen:    "Open AI assistant",
    errorMsg:    "I'm temporarily unavailable. For urgent help please call Alinma at 920001000.",
    toggleLabel: "عربي",
    welcome:     MENU_EN,
    prompts: [
      { label: "1️⃣  Transfer Guardian", value: "1" },
      { label: "2️⃣  SMS Phishing",       value: "2" },
      { label: "3️⃣  Fraud Alerts",        value: "3" },
      { label: "4️⃣  Security Score",      value: "4" },
    ],
  },
  ar: {
    title:       "مساعد SecureAI",
    subtitle:    "متاح 24/7 · مصرف الإنماء",
    placeholder: "اكتب رقماً (1–7) أو اسأل سؤالاً…",
    ariaOpen:    "افتح المساعد الذكي",
    errorMsg:    "أنا غير متاح مؤقتاً. للمساعدة العاجلة، يرجى الاتصال بمصرف الإنماء على 920001000.",
    toggleLabel: "EN",
    welcome:     MENU_AR,
    prompts: [
      { label: "1️⃣  مراقب التحويلات",   value: "1" },
      { label: "2️⃣  رسائل التصيد",       value: "2" },
      { label: "3️⃣  تنبيهات الاحتيال",   value: "3" },
      { label: "4️⃣  درجة الأمان",         value: "4" },
    ],
  },
};

export default function ChatWidget() {
  // Global language drives widget language AND position
  const { lang: globalLang, isAr: globalIsAr } = useLanguage();

  const [open, setOpen]         = useState(false);
  // Internal lang is initialised from — and kept in sync with — the global lang.
  // The user can still override it per-session via the in-widget toggle.
  const [lang, setLang]         = useState(globalLang);
  const [messages, setMessages] = useState([{ role: "assistant", content: globalLang === "ar" ? MENU_AR : MENU_EN }]);
  const [input, setInput]       = useState("");
  const [loading, setLoading]   = useState(false);
  const bottomRef               = useRef(null);
  const inputRef                = useRef(null);

  // Sync widget language whenever the global toggle changes
  useEffect(() => {
    setLang(globalLang);
    setMessages([{ role: "assistant", content: globalLang === "ar" ? MENU_AR : MENU_EN }]);
    setInput("");
  }, [globalLang]);

  const s    = STR[lang];
  const isAr = lang === "ar";

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, open]);
  useEffect(() => { if (open) setTimeout(() => inputRef.current?.focus(), 120); }, [open]);

  function toggleLang() {
    const next = isAr ? "en" : "ar";
    setLang(next);
    setMessages([{ role: "assistant", content: next === "ar" ? MENU_AR : MENU_EN }]);
    setInput("");
  }

  async function sendText(text) {
    if (!text.trim() || loading) return;
    const userMsg = { role: "user", content: text.trim() };
    const next    = [...messages, userMsg];
    setMessages(next);
    setInput("");
    setLoading(true);
    try {
      const { reply } = await sendChatMessage(next.map(({ role, content }) => ({ role, content })), lang);
      setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", content: s.errorMsg }]);
    } finally {
      setLoading(false);
    }
  }

  function send() { sendText(input); }

  const showChips = messages.length === 1 && !loading;

  // Position: bottom-left when global language is Arabic, bottom-right otherwise
  const hPos = globalIsAr ? { left: "1.25rem", right: "auto" } : { right: "1.25rem", left: "auto" };

  return (
    <>
      {/* ── Chat panel ── */}
      <div
        dir={isAr ? "rtl" : "ltr"}
        className={`fixed bottom-20 z-50 flex flex-col rounded-2xl bg-white shadow-2xl ring-1 ring-navy/10 transition-all duration-300 ${
          open ? "w-80 opacity-100 translate-y-0 pointer-events-auto" : "w-80 opacity-0 translate-y-4 pointer-events-none"
        }`}
        style={{ height: "520px", ...hPos }}
      >
        {/* Header */}
        <div className="flex items-center gap-2 rounded-t-2xl bg-navy px-4 py-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-copper/20 text-copper">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-white leading-tight truncate">{s.title}</p>
            <p className="text-[10px] text-white/50">{s.subtitle}</p>
          </div>
          <button onClick={toggleLang}
            className="shrink-0 rounded-md border border-white/20 px-2 py-0.5 text-[11px] font-semibold text-white/80 hover:bg-white/10 hover:text-white transition"
            aria-label="Switch language">
            {s.toggleLabel}
          </button>
          <button onClick={() => setOpen(false)}
            className="shrink-0 text-white/40 hover:text-white transition" aria-label="Close chat">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Message thread */}
        <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
          {messages.map((msg, i) => {
            const isUser = msg.role === "user";
            return (
              <div key={i} className={`flex ${isUser ? (isAr ? "justify-start" : "justify-end") : (isAr ? "justify-end" : "justify-start")}`}>
                {!isUser && (
                  <div className={`${isAr ? "ml-2" : "mr-2"} mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-navy/10`}>
                    <svg className="h-3 w-3 text-navy" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                    </svg>
                  </div>
                )}
                <div className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm leading-snug whitespace-pre-line ${
                  isUser
                    ? "bg-copper text-white " + (isAr ? "rounded-tl-sm" : "rounded-tr-sm")
                    : "bg-navy/5 text-navy "  + (isAr ? "rounded-tr-sm" : "rounded-tl-sm")
                }`}>
                  {msg.content}
                </div>
              </div>
            );
          })}

          {loading && (
            <div className={`flex ${isAr ? "justify-end" : "justify-start"}`}>
              <div className={`${isAr ? "ml-2" : "mr-2"} mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-navy/10`}>
                <svg className="h-3 w-3 text-navy" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
              </div>
              <div className="rounded-2xl bg-navy/5 px-4 py-2.5">
                <span className="flex gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-navy/30 animate-bounce [animation-delay:0ms]" />
                  <span className="h-1.5 w-1.5 rounded-full bg-navy/30 animate-bounce [animation-delay:150ms]" />
                  <span className="h-1.5 w-1.5 rounded-full bg-navy/30 animate-bounce [animation-delay:300ms]" />
                </span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Quick-pick chips */}
        {showChips && (
          <div className="px-3 pb-2 flex flex-wrap gap-1.5">
            {s.prompts.map(({ label, value }) => (
              <button key={value} onClick={() => sendText(value)}
                className="rounded-full border border-navy/15 bg-navy/5 px-2.5 py-1 text-[11px] text-navy/70 hover:bg-copper/10 hover:border-copper/30 hover:text-navy transition">
                {label}
              </button>
            ))}
          </div>
        )}

        {/* Input row */}
        <div className="flex items-center gap-2 border-t border-navy/10 px-3 py-2.5">
          {isAr && (
            <button onClick={send} disabled={!input.trim() || loading}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-copper text-white transition hover:opacity-90 disabled:opacity-40"
              aria-label="Send">
              <svg className="h-4 w-4 rotate-180" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          )}
          <input
            ref={inputRef} type="text" value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            placeholder={s.placeholder}
            dir={isAr ? "rtl" : "ltr"}
            className="flex-1 rounded-lg bg-navy/5 px-3 py-2 text-sm text-navy placeholder-navy/30 outline-none focus:ring-1 focus:ring-copper/40"
          />
          {!isAr && (
            <button onClick={send} disabled={!input.trim() || loading}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-copper text-white transition hover:opacity-90 disabled:opacity-40"
              aria-label="Send">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* ── Floating bubble ── */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="fixed bottom-5 z-50 flex items-center justify-center rounded-full bg-navy shadow-lg ring-2 ring-copper/30 transition hover:scale-105 hover:shadow-xl"
        style={{ height: "52px", width: "52px", ...hPos }}
        aria-label={s.ariaOpen}
      >
        {open ? (
          <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg className="h-5 w-5 text-copper" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
        )}
        {!open && <span className="absolute inset-0 rounded-full animate-ping bg-copper/20" />}
      </button>
    </>
  );
}
