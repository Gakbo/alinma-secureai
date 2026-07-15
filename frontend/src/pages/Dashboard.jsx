import { useEffect, useState } from "react";
import {
  Chart as ChartJS,
  ArcElement,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
} from "chart.js";
import { Doughnut, Bar } from "react-chartjs-2";
import { getAlerts, getDashboardSummary, getHighRiskUsers } from "../api.js";

ChartJS.register(ArcElement, BarElement, CategoryScale, LinearScale, Tooltip, Legend);

const NAVY = "#032341";
const COPPER = "#C36B4E";
const RISK = { high: "#D64545", medium: "#E0A83C", low: "#2E9E6B" };

function StatCard({ label, value }) {
  return (
    <div className="rounded-2xl border border-navy/10 bg-white p-5 shadow-sm">
      <p className="text-xs uppercase tracking-widest text-navy/50">{label}</p>
      <p className="mt-1 font-mono text-3xl font-semibold">{value}</p>
    </div>
  );
}

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [users, setUsers] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getDashboardSummary(), getHighRiskUsers(), getAlerts()])
      .then(([s, u, a]) => {
        setSummary(s);
        setUsers(u);
        setAlerts(a);
      })
      .catch((e) => {
        setError(
          e.response?.status === 403
            ? "This page is for analyst accounts. Sign in as analyst@alinma.com to view it."
            : "Dashboard data could not be loaded. Check that the backend is running."
        );
      });
  }, []);

  if (error) {
    return (
      <div className="mx-auto max-w-4xl">
        <h2 className="text-2xl font-semibold">Analyst Dashboard</h2>
        <p className="mt-6 text-sm text-risk-high">{error}</p>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="mx-auto max-w-4xl">
        <h2 className="text-2xl font-semibold">Analyst Dashboard</h2>
        <p className="mt-6 text-sm text-navy/60">Loading fraud analytics…</p>
      </div>
    );
  }

  const severityCounts = alerts.reduce(
    (acc, a) => ({ ...acc, [a.severity]: (acc[a.severity] || 0) + 1 }),
    {}
  );

  const doughnutData = {
    labels: ["High", "Medium", "Low"],
    datasets: [
      {
        data: [severityCounts.high || 0, severityCounts.medium || 0, severityCounts.low || 0],
        backgroundColor: [RISK.high, RISK.medium, RISK.low],
        borderWidth: 0,
      },
    ],
  };

  const typeCounts = alerts.reduce(
    (acc, a) => ({ ...acc, [a.alert_type]: (acc[a.alert_type] || 0) + 1 }),
    {}
  );

  const barData = {
    labels: Object.keys(typeCounts).map((t) => t.replace("_", " ")),
    datasets: [
      {
        label: "Alerts",
        data: Object.values(typeCounts),
        backgroundColor: COPPER,
        borderRadius: 6,
      },
    ],
  };

  return (
    <div className="mx-auto max-w-5xl">
      <h2 className="text-2xl font-semibold">Analyst Dashboard</h2>
      <p className="mt-1 text-sm text-navy/60">Live fraud picture across the platform.</p>

      <div className="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Total alerts" value={summary.total_alerts} />
        <StatCard label="Open alerts" value={summary.open_alerts} />
        <StatCard label="Fraud SMS today" value={summary.fraud_attempts_today} />
        <StatCard label="Transactions checked" value={summary.total_transactions_checked} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-navy/10 bg-white p-6 shadow-sm">
          <h3 className="text-sm font-semibold">Alerts by severity</h3>
          <div className="mx-auto mt-4 max-w-[260px]">
            <Doughnut
              data={doughnutData}
              options={{ plugins: { legend: { position: "bottom" } }, cutout: "65%" }}
            />
          </div>
        </div>
        <div className="rounded-2xl border border-navy/10 bg-white p-6 shadow-sm">
          <h3 className="text-sm font-semibold">Alerts by attack type</h3>
          <div className="mt-4">
            <Bar
              data={barData}
              options={{
                plugins: { legend: { display: false } },
                scales: {
                  y: { beginAtZero: true, ticks: { precision: 0 } },
                  x: { grid: { display: false } },
                },
              }}
            />
          </div>
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-navy/10 bg-white p-6 shadow-sm">
        <h3 className="text-sm font-semibold">High-risk customers</h3>
        {users.length === 0 ? (
          <p className="mt-3 text-sm text-navy/60">
            No customers currently above the risk threshold.
          </p>
        ) : (
          <table className="mt-3 w-full text-sm">
            <thead>
              <tr className="border-b border-navy/10 text-left text-xs uppercase tracking-wider text-navy/50">
                <th className="py-2">Customer</th>
                <th className="py-2">Behavior risk</th>
                <th className="py-2">Scam exposure</th>
                <th className="py-2">Device trust</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.user_id} className="border-b border-navy/5">
                  <td className="py-2.5 font-medium">{u.name}</td>
                  <td className="py-2.5 font-mono text-risk-high">{u.risk_score}</td>
                  <td className="py-2.5 font-mono">{u.scam_exposure_score}</td>
                  <td className="py-2.5 font-mono">{u.device_trust_score}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
