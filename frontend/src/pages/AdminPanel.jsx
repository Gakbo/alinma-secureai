import { useEffect, useState } from "react";
import { getAdminUsers, updateUserRole } from "../api.js";
import { useLanguage } from "../context/LanguageContext.jsx";
import { T } from "../i18n.js";

const ROLE_COLORS = {
  customer: "bg-blue-100 text-blue-700",
  analyst:  "bg-copper/15 text-copper",
  admin:    "bg-red-100 text-red-700",
};

const ROLES = ["customer", "analyst", "admin"];
const STAFF_DOMAIN = "@alinma.com";

function isRoleInvalid(email, role) {
  const isStaffEmail = email.toLowerCase().endsWith(STAFF_DOMAIN);
  const isStaffRole  = role === "analyst" || role === "admin";
  return (isStaffEmail && !isStaffRole) || (!isStaffEmail && isStaffRole);
}

function roleTooltip(email, role, t) {
  const isStaffEmail = email.toLowerCase().endsWith(STAFF_DOMAIN);
  if (isStaffEmail && role === "customer") return t.role_tip_no_customer;
  if (!isStaffEmail && (role === "analyst" || role === "admin")) {
    const roleName = role.charAt(0).toUpperCase() + role.slice(1);
    return `${t.role_tip_staff_only} ${roleName} ${t.role_tip_role_suffix}`.trim();
  }
  return null;
}

function Toast({ msg, onClose }) {
  useEffect(() => { const t = setTimeout(onClose, 3000); return () => clearTimeout(t); }, [onClose]);
  return (
    <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-xl bg-navy px-4 py-3 text-sm text-white shadow-xl">
      <svg className="h-4 w-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
      </svg>
      {msg}
    </div>
  );
}

export default function AdminPanel() {
  const { lang, isAr } = useLanguage();
  const t = T[lang];

  const [users, setUsers]     = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving]   = useState(null);
  const [toast, setToast]     = useState("");
  const [search, setSearch]   = useState("");

  useEffect(() => {
    getAdminUsers()
      .then(setUsers)
      .catch(() => setUsers([]))
      .finally(() => setLoading(false));
  }, []);

  async function handleRoleChange(userId, newRole) {
    setSaving(userId);
    try {
      await updateUserRole(userId, newRole);
      setUsers((prev) => prev.map((u) => (u.user_id === userId ? { ...u, role: newRole } : u)));
      setToast(t.admin_updated);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setToast(detail || t.admin_failed);
    } finally {
      setSaving(null);
    }
  }

  const filtered = users.filter((u) =>
    u.name.toLowerCase().includes(search.toLowerCase()) ||
    u.email.toLowerCase().includes(search.toLowerCase()) ||
    u.role.toLowerCase().includes(search.toLowerCase())
  );

  const counts = {
    total:    users.length,
    customer: users.filter((u) => u.role === "customer").length,
    analyst:  users.filter((u) => u.role === "analyst").length,
    admin:    users.filter((u) => u.role === "admin").length,
  };

  return (
    <div className="space-y-6" dir={isAr ? "rtl" : "ltr"}>
      {toast && <Toast msg={toast} onClose={() => setToast("")} />}

      <div>
        <h1 className="text-2xl font-bold text-navy">{t.admin_title}</h1>
        <p className="mt-1 text-sm text-navy/50">{t.admin_subtitle}</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          { label: t.admin_total,     value: counts.total,    color: "text-navy" },
          { label: t.admin_customers, value: counts.customer, color: "text-blue-600" },
          { label: t.admin_analysts,  value: counts.analyst,  color: "text-copper" },
          { label: t.admin_admins,    value: counts.admin,    color: "text-red-600" },
        ].map(({ label, value, color }) => (
          <div key={label} className="rounded-xl border border-navy/10 bg-white p-4 shadow-sm">
            <p className="text-xs text-navy/40">{label}</p>
            <p className={`mt-1 text-2xl font-bold ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* User table */}
      <div className="rounded-xl border border-navy/10 bg-white shadow-sm overflow-hidden">
        <div className="flex items-center justify-between border-b border-navy/10 px-5 py-4">
          <h2 className="font-semibold text-navy">{t.admin_all_users}</h2>
          <div className="relative">
            <svg className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-navy/30" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text" value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder={t.admin_search}
              className="rounded-lg border border-navy/20 pl-9 pr-3 py-1.5 text-sm outline-none focus:border-copper"
            />
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16 text-navy/30 text-sm">{t.admin_loading}</div>
        ) : filtered.length === 0 ? (
          <div className="flex items-center justify-center py-16 text-navy/30 text-sm">{t.admin_no_users}</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-navy/5 bg-surface text-xs font-semibold uppercase tracking-wide text-navy/40">
                  <th className="px-5 py-3 text-left">{t.admin_col_name}</th>
                  <th className="px-5 py-3 text-left">{t.admin_col_email}</th>
                  <th className="px-5 py-3 text-left">{t.admin_col_phone}</th>
                  <th className="px-5 py-3 text-left">{t.admin_col_risk}</th>
                  <th className="px-5 py-3 text-left">{t.admin_col_joined}</th>
                  <th className="px-5 py-3 text-left">{t.admin_col_role}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy/5">
                {filtered.map((u) => (
                  <tr key={u.user_id} className="hover:bg-surface/60 transition-colors">
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-2.5">
                        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-navy text-[11px] font-bold uppercase text-white">{u.name.charAt(0)}</div>
                        <span className="font-medium text-navy">{u.name}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3.5 text-navy/60">{u.email}</td>
                    <td className="px-5 py-3.5 text-navy/40">{u.phone || "—"}</td>
                    <td className="px-5 py-3.5">
                      <span className={`font-semibold ${u.risk_score >= 70 ? "text-red-600" : u.risk_score >= 40 ? "text-amber-600" : "text-green-600"}`}>
                        {Math.round(u.risk_score)}
                      </span>
                      <span className="text-navy/30">/100</span>
                    </td>
                    <td className="px-5 py-3.5 text-navy/40">
                      {new Date(u.created_at).toLocaleDateString(lang === "ar" ? "ar-SA" : "en-GB", { day: "2-digit", month: "short", year: "numeric" })}
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-2">
                        <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${ROLE_COLORS[u.role] || ROLE_COLORS.customer}`}>
                          {u.role}
                        </span>
                        <select
                          value={u.role}
                          onChange={(e) => handleRoleChange(u.user_id, e.target.value)}
                          disabled={saving === u.user_id}
                          className="rounded-md border border-navy/20 px-2 py-1 text-xs text-navy outline-none focus:border-copper disabled:opacity-50 cursor-pointer"
                        >
                          {ROLES.map((r) => {
                            const invalid = isRoleInvalid(u.email, r);
                            const tip     = roleTooltip(u.email, r, t);
                            return (
                              <option key={r} value={r} disabled={invalid} title={tip || undefined}>
                                {r.charAt(0).toUpperCase() + r.slice(1)}{invalid ? t.role_unavailable : ""}
                              </option>
                            );
                          })}
                        </select>
                        {saving === u.user_id && (
                          <svg className="h-3.5 w-3.5 animate-spin text-copper" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                          </svg>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
