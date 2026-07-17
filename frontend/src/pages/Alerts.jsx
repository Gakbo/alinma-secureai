import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { getAlerts, updateAlertStatus, acknowledgeAlert } from "../api.js";
import { useLanguage } from "../context/LanguageContext.jsx";
import { T } from "../i18n.js";

const SEV_STYLES = {
  high:   { badge: "bg-risk-high text-white",   row: "border-l-risk-high" },
  medium: { badge: "bg-risk-medium text-white", row: "border-l-risk-medium" },
  low:    { badge: "bg-risk-low text-white",    row: "border-l-risk-low" },
};

const TYPE_ICONS = {
  sms_phishing:           "📨",
  suspicious_transaction: "💸",
  behavior_anomaly:       "📊",
  account_takeover:       "🔓",
  login_anomaly:          "🔑",
  transaction:            "💳",
};

function timeAgo(dateStr, t) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60)  return `${mins}${t.time_min_ago}`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)   return `${hrs}${t.time_hr_ago}`;
  return `${Math.floor(hrs / 24)}${t.time_day_ago}`;
}

// Absolute local date + time, e.g. "17 Jul 2026, 14:30" (Arabic locale when AR).
function fullDateTime(dateStr, lang) {
  return new Date(dateStr).toLocaleString(lang === "ar" ? "ar-SA" : "en-GB", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export default function Alerts() {
  const { user } = useOutletContext() || {};
  const { lang, isAr } = useLanguage();
  const t = T[lang];

  const [alerts, setAlerts]               = useState(null);
  const [error, setError]                 = useState("");
  const [sevFilter, setSevFilter]         = useState("all");
  const [statusFilter, setStatusFilter]   = useState("all");
  const [resolving, setResolving]         = useState({});
  const [acknowledging, setAcknowledging] = useState({});

  const isAnalyst  = user && ["analyst", "admin"].includes(user.role);
  const isCustomer = user && user.role === "customer";

  const SEVERITY_FILTERS = ["all", "high", "medium", "low"];
  const STATUS_FILTERS   = ["all", "open", "resolved"];

  const sevLabel = (f) => ({
    all: t.alerts_all, high: t.alerts_high, medium: t.alerts_medium, low: t.alerts_low,
  }[f] || f);

  useEffect(() => {
    getAlerts()
      .then(setAlerts)
      .catch(() => setError(t.alerts_load_error));
  }, []);

  async function resolve(alertId) {
    setResolving((r) => ({ ...r, [alertId]: true }));
    try {
      const updated = await updateAlertStatus(alertId, "resolved");
      setAlerts((prev) => prev.map((a) => a.alert_id === alertId ? updated : a));
    } catch { /* silent */ } finally { setResolving((r) => ({ ...r, [alertId]: false })); }
  }

  async function acknowledge(alertId) {
    setAcknowledging((s) => ({ ...s, [alertId]: true }));
    try {
      const updated = await acknowledgeAlert(alertId);
      setAlerts((prev) => prev.map((a) => a.alert_id === alertId ? updated : a));
    } catch { /* silent */ } finally { setAcknowledging((s) => ({ ...s, [alertId]: false })); }
  }

  const filtered = (alerts || []).filter((a) => {
    if (sevFilter !== "all" && a.severity !== sevFilter) return false;
    if (statusFilter !== "all" && a.status !== statusFilter) return false;
    return true;
  });

  const counts = (alerts || []).reduce((acc, a) => {
    acc[a.severity] = (acc[a.severity] || 0) + 1;
    acc.open  = (acc.open  || 0) + (a.status === "open" ? 1 : 0);
    acc.total = (acc.total || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="mx-auto max-w-4xl" dir={isAr ? "rtl" : "ltr"}>
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-navy">{t.alerts_title}</h2>
          <p className="mt-1 text-sm text-navy/60">{t.alerts_subtitle}</p>
        </div>
        {counts.total > 0 && (
          <div className="flex gap-3 text-center shrink-0">
            <div className="rounded-xl bg-risk-high/10 px-3 py-2">
              <p className="font-mono text-lg font-bold text-risk-high">{counts.high || 0}</p>
              <p className="text-[10px] uppercase tracking-wide text-risk-high/70">{t.alerts_high}</p>
            </div>
            <div className="rounded-xl bg-amber-50 px-3 py-2">
              <p className="font-mono text-lg font-bold text-risk-medium">{counts.medium || 0}</p>
              <p className="text-[10px] uppercase tracking-wide text-risk-medium/70">{t.alerts_medium}</p>
            </div>
            <div className="rounded-xl bg-emerald-50 px-3 py-2">
              <p className="font-mono text-lg font-bold text-risk-low">{counts.low || 0}</p>
              <p className="text-[10px] uppercase tracking-wide text-risk-low/70">{t.alerts_low}</p>
            </div>
          </div>
        )}
      </div>

      {error && <p className="mt-4 text-sm text-risk-high">⚠️ {error}</p>}

      {/* Filters */}
      {alerts && alerts.length > 0 && (
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <div className="flex rounded-xl border border-navy/10 bg-white p-1 gap-0.5">
            {SEVERITY_FILTERS.map((f) => (
              <button key={f} onClick={() => setSevFilter(f)}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold capitalize transition ${
                  sevFilter === f
                    ? f === "high" ? "bg-risk-high text-white"
                    : f === "medium" ? "bg-risk-medium text-white"
                    : f === "low" ? "bg-risk-low text-white"
                    : "bg-navy text-white"
                    : "text-navy/50 hover:text-navy"
                }`}>
                {f === "all" ? `${sevLabel(f)} (${counts.total || 0})` : sevLabel(f)}
              </button>
            ))}
          </div>
          <div className="flex rounded-xl border border-navy/10 bg-white p-1 gap-0.5">
            {STATUS_FILTERS.map((f) => (
              <button key={f} onClick={() => setStatusFilter(f)}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold capitalize transition ${
                  statusFilter === f ? "bg-navy text-white" : "text-navy/50 hover:text-navy"
                }`}>
                {f === "open" ? `${t.alerts_open_label} (${counts.open || 0})`
                  : f === "all" ? t.alerts_all_status
                  : t.alerts_resolved}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {alerts && filtered.length === 0 && (
        <div className="mt-8 rounded-2xl border border-dashed border-navy/20 bg-white p-12 text-center">
          <p className="text-lg">🛡️</p>
          <p className="mt-2 font-semibold text-navy">
            {alerts.length === 0 ? t.alerts_no_yet : t.alerts_no_match}
          </p>
          <p className="mt-1 text-sm text-navy/60">
            {alerts.length === 0 ? t.alerts_no_yet_sub : t.alerts_no_match_sub}
          </p>
        </div>
      )}

      {/* Alert list */}
      {filtered.length > 0 && (
        <div className="mt-5 space-y-2.5">
          {filtered.map((a) => {
            const sev     = SEV_STYLES[a.severity] || SEV_STYLES.low;
            const icon    = TYPE_ICONS[a.alert_type] || "🔔";
            const typeKey = `type_${a.alert_type}`;
            const label   = t[typeKey] || a.alert_type.replace(/_/g, " ");
            const isOpen  = a.status === "open";
            const sevText = a.severity === "high" ? t.alerts_high : a.severity === "medium" ? t.alerts_medium : t.alerts_low;

            return (
              <div key={a.alert_id}
                className={`flex items-start gap-4 rounded-xl border-l-4 border border-navy/8 bg-white px-5 py-4 shadow-sm transition ${sev.row} ${isOpen ? "" : "opacity-60"}`}>
                <span className="mt-0.5 text-xl shrink-0">{icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold uppercase ${sev.badge}`}>{sevText}</span>
                    <span className="text-sm font-semibold text-navy capitalize">{label}</span>
                    {!isOpen && (
                      <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold uppercase text-emerald-700">
                        {t.alerts_resolved}
                      </span>
                    )}
                    {isOpen && a.acknowledged_by_customer && (
                      <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold uppercase text-blue-600">
                        {t.alerts_seen}
                      </span>
                    )}
                  </div>
                  {a.description && <p className="mt-1.5 text-sm text-navy/70 leading-relaxed">{a.description}</p>}
                </div>
                <div className="shrink-0 text-right">
                  <p className="text-xs font-medium text-navy/50" title={fullDateTime(a.created_at, lang)}>{timeAgo(a.created_at, t)}</p>
                  <p className="text-[10px] text-navy/35">{fullDateTime(a.created_at, lang)}</p>
                  {isAnalyst && isOpen && (
                    <button onClick={() => resolve(a.alert_id)} disabled={resolving[a.alert_id]}
                      className="mt-2 flex items-center gap-1 rounded-lg bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700 transition hover:bg-emerald-100 disabled:opacity-50">
                      {resolving[a.alert_id] ? "…" : t.alerts_resolve}
                    </button>
                  )}
                  {isCustomer && isOpen && !a.acknowledged_by_customer && (
                    <button onClick={() => acknowledge(a.alert_id)} disabled={acknowledging[a.alert_id]}
                      className="mt-2 flex items-center gap-1 rounded-lg bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-600 transition hover:bg-blue-100 disabled:opacity-50">
                      {acknowledging[a.alert_id] ? "…" : t.alerts_acknowledge}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
