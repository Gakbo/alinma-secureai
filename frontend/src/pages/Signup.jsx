import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register } from "../api.js";
import { useLanguage } from "../context/LanguageContext.jsx";
import { T } from "../i18n.js";

const STAFF_DOMAIN = "@alinma.com";
const isStaffEmail = (e) => e.toLowerCase().endsWith(STAFF_DOMAIN);

export default function Signup() {
  const navigate = useNavigate();
  const { lang, setLang, isAr } = useLanguage();
  const t = T[lang];

  const [form, setForm]           = useState({ name: "", email: "", phone: "", password: "", confirm: "" });
  const [emailError, setEmailError] = useState("");
  const [error, setError]         = useState("");
  const [loading, setLoading]     = useState(false);

  function set(field) {
    return (e) => {
      setForm((f) => ({ ...f, [field]: e.target.value }));
      if (field === "email") setEmailError("");
    };
  }

  function checkEmailDomain() {
    if (form.email && isStaffEmail(form.email)) {
      setEmailError(t.signup_err_staff);
      return false;
    }
    setEmailError("");
    return true;
  }

  async function handleSubmit() {
    setError("");
    if (!checkEmailDomain()) return;
    if (form.password !== form.confirm) { setError(t.err_pw_mismatch); return; }
    if (form.password.length < 8)       { setError(t.err_pw_short); return; }
    setLoading(true);
    try {
      await register(form.name, form.email, form.phone, form.password);
      navigate("/sms");
    } catch (err) {
      setError(err.response?.data?.detail || t.signup_err_failed);
    } finally {
      setLoading(false);
    }
  }

  const isAlinmaEmail = isStaffEmail(form.email);
  const valid = form.name && form.email && form.password && form.confirm && !isAlinmaEmail;

  return (
    <div className="flex min-h-screen items-center justify-center bg-navy px-4 py-10" dir={isAr ? "rtl" : "ltr"}>
      {/* Language toggle */}
      <button
        onClick={() => setLang(isAr ? "en" : "ar")}
        className="absolute top-4 right-4 z-20 rounded-lg border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-semibold text-white hover:bg-white/20 transition"
      >
        🌐 {t.lang_toggle}
      </button>

      <div className="w-full max-w-md">
        {/* Brand */}
        <div className="mb-8 text-center text-white">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-copper/20">
            <svg className="h-6 w-6 text-copper" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
          </div>
          <p className="font-mono text-xs uppercase tracking-widest text-copper">Alinma</p>
          <h1 className="text-3xl font-semibold">SecureAI</h1>
          <p className="mt-1 text-sm text-white/50">{t.signup_tagline}</p>
        </div>

        <div className="rounded-2xl bg-white p-8 shadow-xl">
          <h2 className="mb-5 text-lg font-semibold text-navy">{t.signup_heading}</h2>

          <label className="block text-sm font-medium text-navy">{t.signup_name} <span className="text-red-400">*</span></label>
          <input type="text" value={form.name} onChange={set("name")} placeholder="Khalid Al-Mansour"
            className="mt-1.5 w-full rounded-lg border border-navy/20 px-3 py-2.5 text-sm outline-none focus:border-copper focus:ring-1 focus:ring-copper/30" />

          <label className="mt-4 block text-sm font-medium text-navy">{t.signup_email} <span className="text-red-400">*</span></label>
          <input type="email" value={form.email} onChange={set("email")} onBlur={checkEmailDomain}
            placeholder="you@example.com"
            className={`mt-1.5 w-full rounded-lg border px-3 py-2.5 text-sm outline-none focus:ring-1 ${
              emailError ? "border-amber-400 focus:border-amber-500 focus:ring-amber-200" : "border-navy/20 focus:border-copper focus:ring-copper/30"
            }`} />
          {emailError && (
            <div className="mt-2 flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2.5 text-xs text-amber-800">
              <svg className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{emailError}{" "}
                <Link to="/login" className="font-semibold underline hover:text-amber-900">{t.signup_staff_link}</Link>
              </span>
            </div>
          )}

          <label className="mt-4 block text-sm font-medium text-navy">
            {t.signup_phone} <span className="text-navy/30 text-xs font-normal">{t.signup_phone_opt}</span>
          </label>
          <input type="tel" value={form.phone} onChange={set("phone")} placeholder="+966 5X XXX XXXX"
            className="mt-1.5 w-full rounded-lg border border-navy/20 px-3 py-2.5 text-sm outline-none focus:border-copper focus:ring-1 focus:ring-copper/30" />

          <label className="mt-4 block text-sm font-medium text-navy">{t.signup_password} <span className="text-red-400">*</span></label>
          <input type="password" value={form.password} onChange={set("password")} placeholder={t.signup_min}
            className="mt-1.5 w-full rounded-lg border border-navy/20 px-3 py-2.5 text-sm outline-none focus:border-copper focus:ring-1 focus:ring-copper/30" />

          <label className="mt-4 block text-sm font-medium text-navy">{t.signup_confirm} <span className="text-red-400">*</span></label>
          <input type="password" value={form.confirm} onChange={set("confirm")}
            onKeyDown={(e) => e.key === "Enter" && valid && handleSubmit()} placeholder={t.signup_repeat}
            className="mt-1.5 w-full rounded-lg border border-navy/20 px-3 py-2.5 text-sm outline-none focus:border-copper focus:ring-1 focus:ring-copper/30" />

          {error && <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}

          <button onClick={handleSubmit} disabled={loading || !valid}
            className="mt-6 w-full rounded-lg bg-copper py-2.5 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-40">
            {loading ? t.signup_creating : t.signup_create}
          </button>

          <p className="mt-5 text-center text-sm text-navy/50">
            {t.signup_have_acct}{" "}
            <Link to="/login" className="font-semibold text-copper hover:underline">{t.signup_sign_in}</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
