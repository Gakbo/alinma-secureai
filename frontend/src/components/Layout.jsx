import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { getMe } from "../api.js";
import { useLanguage } from "../context/LanguageContext.jsx";
import { T } from "../i18n.js";
import ChatWidget from "./ChatWidget.jsx";

// Inline SVG icons
const Icons = {
  shield: (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  ),
  sms: (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
    </svg>
  ),
  transfer: (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
    </svg>
  ),
  score: (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
    </svg>
  ),
  bell: (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
    </svg>
  ),
  chart: (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
  ),
  admin: (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  ),
};

// Nav config uses translation keys
const navConfig = [
  { to: "/sms",          labelKey: "nav_sms",       hintKey: "nav_hint_sms",       icon: "sms" },
  { to: "/transactions", labelKey: "nav_transfer",   hintKey: "nav_hint_transfer",  icon: "transfer" },
  { to: "/score",        labelKey: "nav_score",      hintKey: "nav_hint_score",     icon: "score",  customerOnly: true },
  { to: "/alerts",       labelKey: "nav_alerts",     hintKey: "nav_hint_alerts",    icon: "bell" },
  { to: "/dashboard",    labelKey: "nav_dashboard",  hintKey: "nav_hint_dashboard", icon: "chart",  analystOnly: true },
  { to: "/admin",        labelKey: "nav_admin",      hintKey: "nav_hint_admin",     icon: "admin",  adminOnly: true },
];

const ROLE_BADGE = {
  customer: "bg-white/10 text-white/80",
  analyst:  "bg-copper/20 text-copper",
  admin:    "bg-red-400/20 text-red-300",
};

export default function Layout() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const { lang, setLang, isAr } = useLanguage();
  const s = T[lang];

  useEffect(() => {
    getMe().then(setUser).catch(() => {});
  }, []);

  const isAdmin    = user?.role === "admin";
  const isAnalyst  = user && ["analyst", "admin"].includes(user.role);
  const isCustomer = user?.role === "customer";

  function logout() {
    localStorage.removeItem("token");
    navigate("/login");
  }

  const visibleNav = navConfig.filter((n) => {
    if (n.adminOnly    && !isAdmin)    return false;
    if (n.analystOnly  && !isAnalyst)  return false;
    if (n.customerOnly && !isCustomer) return false;
    return true;
  });

  return (
    <div dir={isAr ? "rtl" : "ltr"} className="flex min-h-screen bg-surface">
      <aside className="flex w-64 shrink-0 flex-col bg-navy text-white shadow-xl">
        {/* Brand */}
        <div className="border-b border-white/10 px-6 py-5">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-copper/20 text-copper">
              {Icons.shield}
            </div>
            <div>
              <p className="font-mono text-[10px] uppercase tracking-widest text-copper">Alinma Bank</p>
              <h1 className="text-base font-bold leading-tight">SecureAI</h1>
            </div>
          </div>
          <p className="mt-2 text-[11px] text-white/50">{s.nav_tagline}</p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-0.5 px-3 py-4">
          {visibleNav.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              className={({ isActive }) =>
                `flex items-start gap-3 rounded-lg px-3 py-2.5 transition-all duration-150 ${
                  isActive
                    ? "bg-copper text-white shadow-sm"
                    : "text-white/65 hover:bg-white/8 hover:text-white"
                }`
              }
            >
              <span className="mt-0.5 shrink-0 opacity-80">{Icons[n.icon]}</span>
              <span>
                <span className="block text-sm font-medium leading-tight">{s[n.labelKey]}</span>
                <span className="block text-[11px] opacity-60 mt-0.5">{s[n.hintKey]}</span>
              </span>
            </NavLink>
          ))}
        </nav>

        {/* User section */}
        <div className="border-t border-white/10 px-4 py-4">
          {user && (
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10 text-xs font-bold uppercase">
                {user.name.charAt(0)}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium leading-tight">{user.name}</p>
                <span className={`mt-0.5 inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold capitalize ${ROLE_BADGE[user.role] || ROLE_BADGE.customer}`}>
                  {user.role}
                </span>
              </div>
            </div>
          )}

          {/* Language toggle */}
          <button
            onClick={() => setLang(isAr ? "en" : "ar")}
            className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-lg border border-white/20 px-2 py-1.5 text-xs font-semibold text-white/70 transition hover:bg-white/10 hover:text-white"
          >
            🌐 {s.lang_toggle}
          </button>

          <button
            onClick={logout}
            className="mt-2 flex w-full items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs text-white/50 transition hover:bg-white/10 hover:text-white"
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            {s.nav_signout}
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto px-8 py-8">
        <Outlet context={{ user }} />
      </main>

      {/* AI chat widget — customers only */}
      {isCustomer && <ChatWidget />}
    </div>
  );
}
