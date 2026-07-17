import { useState, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { resetPassword } from "../api.js";
import { useLanguage } from "../context/LanguageContext.jsx";
import { T } from "../i18n.js";

export default function ResetPassword() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";

  const { lang, setLang, isAr } = useLanguage();
  const t = T[lang];

  const [password, setPassword] = useState("");
  const [confirm, setConfirm]   = useState("");
  const [loading, setLoading]   = useState(false);
  const [success, setSuccess]   = useState(false);
  const [error, setError]       = useState("");

  useEffect(() => {
    if (!token) setError(t.reset_err_no_token);
  }, [token]);

  async function handleSubmit() {
    setError("");
    if (password.length < 8) { setError(t.err_pw_short); return; }
    if (password !== confirm) { setError(t.err_pw_mismatch); return; }
    setLoading(true);
    try {
      await resetPassword(token, password);
      setSuccess(true);
      setTimeout(() => navigate("/login"), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || t.reset_err_failed);
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
          {success ? (
            <>
              <div className="mb-5 flex items-center justify-center">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
                  <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              </div>
              <h2 className="text-center text-lg font-semibold text-navy">{t.reset_success_title}</h2>
              <p className="mt-2 text-center text-sm text-navy/50">{t.reset_success_sub}</p>
              <button onClick={() => navigate("/login")}
                className="mt-5 w-full rounded-lg bg-copper py-2.5 text-sm font-semibold text-white transition hover:opacity-90">
                {t.reset_sign_in}
              </button>
            </>
          ) : (
            <>
              <h2 className="mb-1 text-lg font-semibold text-navy">{t.reset_title}</h2>
              <p className="mb-5 text-sm text-navy/50">{t.reset_subtitle}</p>

              <label className="block text-sm font-medium text-navy">{t.reset_new_pw}</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                placeholder={t.signup_min} disabled={!token}
                className="mt-1.5 w-full rounded-lg border border-navy/20 px-3 py-2.5 text-sm outline-none focus:border-copper focus:ring-1 focus:ring-copper/30 disabled:opacity-50" />

              <label className="mt-4 block text-sm font-medium text-navy">{t.reset_confirm_pw}</label>
              <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && password && confirm && handleSubmit()}
                placeholder={t.signup_repeat} disabled={!token}
                className="mt-1.5 w-full rounded-lg border border-navy/20 px-3 py-2.5 text-sm outline-none focus:border-copper focus:ring-1 focus:ring-copper/30 disabled:opacity-50" />

              {error && <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}

              <button onClick={handleSubmit} disabled={loading || !password || !confirm || !token}
                className="mt-5 w-full rounded-lg bg-copper py-2.5 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-40">
                {loading ? t.reset_saving : t.reset_set}
              </button>

              <p className="mt-5 text-center text-sm text-navy/50">
                <Link to="/forgot-password" className="font-semibold text-copper hover:underline">{t.reset_request_new}</Link>
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
