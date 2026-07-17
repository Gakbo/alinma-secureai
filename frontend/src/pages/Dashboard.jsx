import { useEffect, useState } from "react";
import {
  Chart as ChartJS, ArcElement, BarElement, LineElement, PointElement,
  CategoryScale, LinearScale, Tooltip, Legend, Filler,
} from "chart.js";
import { Doughnut, Bar, Line } from "react-chartjs-2";
import { getAlerts, getDashboardSummary, getHighRiskUsers, getFraudTrend, getRegionStats } from "../api.js";
import { useLanguage } from "../context/LanguageContext.jsx";
import { T } from "../i18n.js";

ChartJS.register(ArcElement, BarElement, LineElement, PointElement, CategoryScale, LinearScale, Tooltip, Legend, Filler);

const COPPER = "#C36B4E";
const RISK   = { high: "#D64545", medium: "#E0A83C", low: "#2E9E6B" };

const TYPE_ICON = {
  sms_phishing: "📨", suspicious_transaction: "💸", behavior_anomaly: "📊",
  account_takeover: "🔓", login_anomaly: "🔑", transaction: "💳",
};

function StatCard({ label, value, sub, icon, accent }) {
  return (
    <div className="rounded-2xl border border-navy/8 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-widest text-navy/40">{label}</p>
        <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-base ${accent || "bg-surface"}`}>{icon}</span>
      </div>
      <p className="mt-2 font-mono text-3xl font-bold text-navy">{value ?? "—"}</p>
      {sub && <p className="mt-1 text-xs text-navy/50">{sub}</p>}
    </div>
  );
}

function timeAgo(dateStr, t) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60)  return `${mins}${t.time_min_ago}`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)   return `${hrs}${t.time_hr_ago}`;
  return `${Math.floor(hrs / 24)}${t.time_day_ago}`;
}

export default function Dashboard() {
  const { lang, isAr } = useLanguage();
  const t = T[lang];

  const [summary, setSummary] = useState(null);
  const [users,   setUsers]   = useState([]);
  const [alerts,  setAlerts]  = useState([]);
  const [trend,   setTrend]   = useState([]);
  const [regions, setRegions] = useState([]);
  const [error,   setError]   = useState("");

  useEffect(() => {
    Promise.all([getDashboardSummary(), getHighRiskUsers(), getAlerts(), getFraudTrend(), getRegionStats()])
      .then(([s, u, a, tr, r]) => { setSummary(s); setUsers(u); setAlerts(a); setTrend(tr); setRegions(r); })
      .catch((e) => setError(e.response?.status === 403 ? t.dash_err_403 : t.dash_err_general));
  }, []);

  if (error) return (
    <div className="mx-auto max-w-5xl" dir={isAr ? "rtl" : "ltr"}>
      <h2 className="text-2xl font-bold">{t.dash_title}</h2>
      <div className="mt-6 rounded-2xl border border-risk-high/20 bg-risk-high/5 p-6">
        <p className="text-sm text-risk-high">⚠️ {error}</p>
      </div>
    </div>
  );

  if (!summary) return (
    <div className="mx-auto max-w-5xl" dir={isAr ? "rtl" : "ltr"}>
      <h2 className="text-2xl font-bold">{t.dash_title}</h2>
      <p className="mt-6 text-sm text-navy/50">{t.dash_loading}</p>
    </div>
  );

  const severityCounts = alerts.reduce((acc, a) => ({ ...acc, [a.severity]: (acc[a.severity] || 0) + 1 }), {});
  const doughnutData = {
    labels: [t.alerts_high, t.alerts_medium, t.alerts_low],
    datasets: [{ data: [severityCounts.high || 0, severityCounts.medium || 0, severityCounts.low || 0], backgroundColor: [RISK.high, RISK.medium, RISK.low], borderWidth: 0 }],
  };

  const typeCounts = alerts.reduce((acc, a) => ({ ...acc, [a.alert_type]: (acc[a.alert_type] || 0) + 1 }), {});
  const barData = {
    labels: Object.keys(typeCounts).map((type) => t[`type_${type}`] || type.replace(/_/g, " ")),
    datasets: [{ label: t.alerts_title, data: Object.values(typeCounts), backgroundColor: COPPER, borderRadius: 6 }],
  };

  const trendData = {
    labels: trend.map((d) => d.date),
    datasets: [{ label: t.alerts_title, data: trend.map((d) => d.count), fill: true, borderColor: COPPER, backgroundColor: "rgba(195,107,78,0.12)", pointBackgroundColor: COPPER, pointRadius: 4, tension: 0.4 }],
  };

  const regionData = {
    labels: regions.map((r) => r.region),
    datasets: [{ label: t.dash_by_region, data: regions.map((r) => r.count), backgroundColor: regions.map((r) => r.count >= 4 ? RISK.high : r.count >= 2 ? RISK.medium : RISK.low), borderRadius: 5 }],
  };

  const openAlerts = alerts.filter((a) => a.status === "open").slice(0, 5);
  const chartOpts = {
    plugins: { legend: { display: false } },
    scales: { y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: "#f0f0f0" } }, x: { grid: { display: false } } },
    maintainAspectRatio: true,
  };

  return (
    <div className="mx-auto max-w-6xl" dir={isAr ? "rtl" : "ltr"}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-navy">{t.dash_title}</h2>
          <p className="mt-1 text-sm text-navy/50">{t.dash_subtitle}</p>
        </div>
        <div className="flex items-center gap-2 rounded-xl bg-emerald-50 border border-emerald-200 px-3 py-2">
          <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
          <span className="text-xs font-semibold text-emerald-700">{t.dash_live}</span>
        </div>
      </div>

      {/* Stat cards */}
      <div className="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-6">
        <StatCard label={t.dash_total_alerts} value={summary.total_alerts}               icon="🔔" accent="bg-copper/10" />
        <StatCard label={t.dash_open_alerts}  value={summary.open_alerts}                icon="🚨" accent="bg-risk-high/10" sub={summary.open_alerts > 0 ? t.dash_needs : t.dash_clear} />
        <StatCard label={t.dash_high_risk}    value={summary.high_risk_users}            icon="👤" accent="bg-amber-50" />
        <StatCard label={t.dash_fraud_sms}    value={summary.fraud_attempts_today}       icon="📨" accent="bg-purple-50" />
        <StatCard label={t.dash_transfers}    value={summary.total_transactions_checked} icon="💸" accent="bg-blue-50" />
        <StatCard label={t.dash_avg_risk}     value={`${(summary.average_transaction_risk * 100).toFixed(0)}%`} icon="📊" accent="bg-surface" />
      </div>

      {/* Charts row 1 */}
      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 rounded-2xl border border-navy/8 bg-white p-6 shadow-sm">
          <h3 className="text-sm font-semibold text-navy">{t.dash_trend}</h3>
          <div className="mt-4">
            <Line data={trendData} options={{ ...chartOpts, plugins: { legend: { display: false } }, maintainAspectRatio: false }} height={160} />
          </div>
        </div>
        <div className="rounded-2xl border border-navy/8 bg-white p-6 shadow-sm">
          <h3 className="text-sm font-semibold text-navy">{t.dash_by_sev}</h3>
          <div className="mx-auto mt-3 max-w-[200px]">
            <Doughnut data={doughnutData} options={{ plugins: { legend: { position: "bottom", labels: { boxWidth: 10, font: { size: 11 } } } }, cutout: "68%" }} />
          </div>
        </div>
      </div>

      {/* Charts row 2 */}
      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-navy/8 bg-white p-6 shadow-sm">
          <h3 className="text-sm font-semibold text-navy">{t.dash_by_type}</h3>
          <div className="mt-4"><Bar data={barData} options={{ ...chartOpts, plugins: { legend: { display: false } } }} /></div>
        </div>
        <div className="rounded-2xl border border-navy/8 bg-white p-6 shadow-sm">
          <h3 className="text-sm font-semibold text-navy">{t.dash_by_region}</h3>
          <div className="mt-4"><Bar data={regionData} options={{ ...chartOpts, plugins: { legend: { display: false } } }} /></div>
        </div>
      </div>

      {/* Bottom row */}
      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-navy/8 bg-white p-6 shadow-sm">
          <h3 className="text-sm font-semibold text-navy flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-risk-high animate-pulse" />
            {t.dash_open_req}
          </h3>
          {openAlerts.length === 0 ? (
            <p className="mt-4 text-sm text-navy/50">{t.dash_all_resolved}</p>
          ) : (
            <div className="mt-4 space-y-2.5">
              {openAlerts.map((a) => {
                const label   = t[`type_${a.alert_type}`] || a.alert_type.replace(/_/g, " ");
                const sevText = a.severity === "high" ? t.alerts_high : a.severity === "medium" ? t.alerts_medium : t.alerts_low;
                return (
                  <div key={a.alert_id} className="flex items-start gap-3 rounded-xl bg-surface p-3">
                    <span className="text-lg">{TYPE_ICON[a.alert_type] || "🔔"}</span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase text-white ${
                          a.severity === "high" ? "bg-risk-high" : a.severity === "medium" ? "bg-risk-medium" : "bg-risk-low"
                        }`}>{sevText}</span>
                        <span className="text-xs font-medium text-navy capitalize">{label}</span>
                      </div>
                      {a.description && <p className="mt-0.5 truncate text-xs text-navy/60">{a.description}</p>}
                    </div>
                    <span className="shrink-0 text-[10px] text-navy/40">{timeAgo(a.created_at, t)}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-navy/8 bg-white p-6 shadow-sm">
          <h3 className="text-sm font-semibold text-navy">{t.dash_high_customers}</h3>
          {users.length === 0 ? (
            <p className="mt-4 text-sm text-navy/50">{t.dash_no_high}</p>
          ) : (
            <table className="mt-4 w-full text-sm">
              <thead>
                <tr className="border-b border-navy/8 text-left">
                  <th className="pb-2 text-xs font-semibold uppercase tracking-wider text-navy/40">{t.dash_col_customer}</th>
                  <th className="pb-2 text-xs font-semibold uppercase tracking-wider text-navy/40">{t.dash_col_risk}</th>
                  <th className="pb-2 text-xs font-semibold uppercase tracking-wider text-navy/40 hidden sm:table-cell">{t.dash_col_exposure}</th>
                  <th className="pb-2 text-xs font-semibold uppercase tracking-wider text-navy/40 hidden sm:table-cell">{t.dash_col_device}</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.user_id} className="border-b border-navy/5">
                    <td className="py-2.5">
                      <div className="flex items-center gap-2">
                        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-navy/10 text-[10px] font-bold uppercase text-navy">{u.name.charAt(0)}</div>
                        <span className="font-medium text-navy text-xs">{u.name.split(" ")[0]}</span>
                      </div>
                    </td>
                    <td className="py-2.5">
                      <span className={`font-mono text-sm font-bold ${u.risk_score >= 70 ? "text-risk-high" : u.risk_score >= 40 ? "text-risk-medium" : "text-risk-low"}`}>{u.risk_score}</span>
                    </td>
                    <td className="py-2.5 font-mono text-xs text-navy/60 hidden sm:table-cell">{u.scam_exposure_score}</td>
                    <td className="py-2.5 font-mono text-xs text-navy/60 hidden sm:table-cell">{u.device_trust_score}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
