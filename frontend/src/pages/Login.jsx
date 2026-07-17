import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { login, getTokenRole } from "../api.js";
import { useLanguage } from "../context/LanguageContext.jsx";
import { T } from "../i18n.js";

const STAFF_DOMAIN = "@alinma.com";
const isStaffEmail = (e) => e.toLowerCase().endsWith(STAFF_DOMAIN);

function roleHome(role) {
  if (role === "admin")   return "/admin";
  if (role === "analyst") return "/dashboard";
  return "/sms";
}

export default function Login() {
  const navigate = useNavigate();
  const { lang, setLang, isAr } = useLanguage();
  const t = T[lang];

  const [tab, setTab]         = useState("customer");
  const [email, setEmail]     = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]     = useState("");
  const [loading, setLoading] = useState(false);

  function switchTab(next) { setTab(next); setError(""); }

  function validateDomain() {
    if (tab === "staff" && email && !isStaffEmail(email)) {
      setError(t.login_err_staff_domain);
      return false;
    }
    if (tab === "customer" && email && isStaffEmail(email)) {
      setError(t.login_err_customer_tab);
      return false;
    }
    return true;
  }

  async function handleSubmit() {
    setError("");
    if (!validateDomain()) return;
    setLoading(true);
    try {
      await login(email, password);
      navigate(roleHome(getTokenRole()));
    } catch (err) {
      setError(err.response?.data?.detail || t.login_err_invalid);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-navy px-4" dir={isAr ? "rtl" : "ltr"}>
      {/* Background layers */}
      <div className="pointer-events-none absolute -right-40 -top-40 h-[700px] w-[700px] rounded-full"
        style={{ background: "radial-gradient(circle, rgba(195,107,78,0.38) 0%, transparent 68%)" }} />
      <div className="pointer-events-none absolute -bottom-32 -left-32 h-[500px] w-[500px] rounded-full"
        style={{ background: "radial-gradient(circle, rgba(195,107,78,0.22) 0%, transparent 68%)" }} />
      <div className="pointer-events-none absolute inset-0"
        style={{ background: "radial-gradient(ellipse 60% 70% at 50% 50%, transparent 40%, rgba(3,35,65,0.6) 100%)" }} />
      <div className="pointer-events-none absolute inset-0 opacity-[0.045]"
        style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='44' height='44' viewBox='0 0 44 44' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M0 44L44 0M-4 4L4 -4M40 48L48 40' stroke='%23ffffff' stroke-width='1.2' fill='none'/%3E%3C/svg%3E\")", backgroundSize: "44px 44px" }} />

      {/* Language toggle */}
      <button
        onClick={() => setLang(isAr ? "en" : "ar")}
        className="absolute top-4 right-4 z-20 rounded-lg border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-semibold text-white hover:bg-white/20 transition"
      >
        🌐 {t.lang_toggle}
      </button>

      <div className="relative z-10 w-full max-w-md">
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

        <div className="rounded-2xl bg-white shadow-xl overflow-hidden">
          {/* Tab switcher */}
          <div className="flex border-b border-navy/10">
            <button onClick={() => switchTab("customer")}
              className={`flex-1 py-3.5 text-sm font-semibold transition-colors ${tab === "customer" ? "bg-navy text-white" : "bg-white text-navy/50 hover:text-navy"}`}>
              <span className="mr-1.5">👤</span> {t.login_customer}
            </button>
            <button onClick={() => switchTab("staff")}
              className={`flex-1 py-3.5 text-sm font-semibold transition-colors ${tab === "staff" ? "bg-navy text-white" : "bg-white text-navy/50 hover:text-navy"}`}>
              <span className="mr-1.5">🔐</span> {t.login_employee}
            </button>
          </div>

          <div className="p-8">
            <label className="block text-sm font-medium text-navy">
              {tab === "staff" ? t.login_work_email : t.login_email}
            </label>
            <input
              type="email" value={email}
              onChange={(e) => { setEmail(e.target.value); setError(""); }}
              onBlur={validateDomain}
              placeholder={tab === "staff" ? "you@alinma.com" : "you@example.com"}
              className="mt-1.5 w-full rounded-lg border border-navy/20 px-3 py-2.5 text-sm outline-none focus:border-copper focus:ring-1 focus:ring-copper/30"
            />

            <label className="mt-4 block text-sm font-medium text-navy">{t.login_password}</label>
            <input
              type="password" value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
              className="mt-1.5 w-full rounded-lg border border-navy/20 px-3 py-2.5 text-sm outline-none focus:border-copper focus:ring-1 focus:ring-copper/30"
            />

            {error && <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}

            <button onClick={handleSubmit} disabled={loading || !email || !password}
              className="mt-5 w-full rounded-lg bg-copper py-2.5 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-40">
              {loading ? t.login_signing : t.login_sign_in}
            </button>

            <div className="mt-4 text-center">
              <Link to="/forgot-password" className="text-xs text-navy/40 hover:text-copper hover:underline">
                {t.login_forgot}
              </Link>
            </div>

            {tab === "customer" && (
              <p className="mt-4 text-center text-sm text-navy/50">
                {t.login_new}{" "}
                <Link to="/signup" className="font-semibold text-copper hover:underline">{t.login_create}</Link>
              </p>
            )}

            <p className="mt-4 text-center text-xs text-navy/30">
              Demo: <code>analyst@alinma.com</code> · <code>admin@alinma.com</code>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
