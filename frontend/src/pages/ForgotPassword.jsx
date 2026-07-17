import { useState } from "react";
import { Link } from "react-router-dom";
import { forgotPassword } from "../api.js";
import { useLanguage } from "../context/LanguageContext.jsx";
import { T } from "../i18n.js";

export default function ForgotPassword() {
  const { lang, setLang, isAr } = useLanguage();
  const t = T[lang];

  const [email, setEmail]     = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent]       = useState(false);
  const [error, setError]     = useState("");

  async function handleSubmit() {
    setError("");
    setLoading(true);
    try {
      await forgotPassword(email);
      setSent(true);
    } catch {
      setError(t.err_generic);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-navy px-4" dir={isAr ? "rtl" : "ltr"}>
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
          <p className="mt-1 text-sm text-white/50">{t.login_tagline}</p>
        </div>

        <div className="rounded-2xl bg-white p-8 shadow-xl">
          {sent ? (
            <div className="text-center">
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-green-100">
                <svg className="h-7 w-7 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-navy">{t.forgot_check_title}</h2>
              <p className="mt-2 text-center text-sm text-navy/50">
                {t.forgot_check_pre} <strong>{email}</strong> {t.forgot_check_post}
              </p>
              <Link to="/login" className="mt-5 block text-center text-sm font-semibold text-copper hover:underline">
                {t.forgot_back_signin}
              </Link>
            </div>
          ) : (
            <>
              <h2 className="text-lg font-semibold text-navy">{t.forgot_title}</h2>
              <p className="mt-1 text-sm text-navy/50">{t.forgot_subtitle}</p>

              <label className="mt-5 block text-sm font-medium text-navy">{t.forgot_email}</label>
              <input
                type="email" value={email}
                onChange={(e) => setEmail(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && email && handleSubmit()}
                placeholder="you@example.com"
                className="mt-1.5 w-full rounded-lg border border-navy/20 px-3 py-2.5 text-sm outline-none focus:border-copper focus:ring-1 focus:ring-copper/30"
              />

              {error && <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}

              <button onClick={handleSubmit} disabled={loading || !email}
                className="mt-5 w-full rounded-lg bg-copper py-2.5 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-40">
                {loading ? t.forgot_sending : t.forgot_send}
              </button>

              <p className="mt-5 text-center text-sm text-navy/50">
                {t.forgot_remember}{" "}
                <Link to="/login" className="font-semibold text-copper hover:underline">{t.forgot_back}</Link>
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
