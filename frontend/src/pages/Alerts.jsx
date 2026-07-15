import { useEffect, useState } from "react";
import { getAlerts } from "../api.js";

const SEVERITY_BADGE = {
  high: "bg-risk-high",
  medium: "bg-risk-medium",
  low: "bg-risk-low",
};

export default function Alerts() {
  const [alerts, setAlerts] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getAlerts()
      .then(setAlerts)
      .catch(() => setError("Alerts could not be loaded. Check that the backend is running."));
  }, []);

  return (
    <div className="mx-auto max-w-4xl">
      <h2 className="text-2xl font-semibold">Fraud Alerts</h2>
      <p className="mt-1 text-sm text-navy/60">
        Every high-risk SMS or transaction generates an alert automatically.
      </p>

      {error && <p className="mt-6 text-sm text-risk-high">{error}</p>}

      {alerts && alerts.length === 0 && (
        <div className="mt-6 rounded-2xl border border-dashed border-navy/20 bg-white p-10 text-center">
          <p className="font-medium">No alerts yet</p>
          <p className="mt-1 text-sm text-navy/60">
            Analyze a phishing SMS or a high-risk transfer to generate the first alert.
          </p>
        </div>
      )}

      {alerts && alerts.length > 0 && (
        <div className="mt-6 space-y-3">
          {alerts.map((a) => (
            <div
              key={a.alert_id}
              className="flex items-start justify-between gap-4 rounded-xl border border-navy/10 bg-white p-4 shadow-sm"
            >
              <div>
                <div className="flex items-center gap-2">
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase text-white ${
                      SEVERITY_BADGE[a.severity] || "bg-navy"
                    }`}
                  >
                    {a.severity}
                  </span>
                  <span className="text-sm font-medium capitalize">
                    {a.alert_type.replace("_", " ")}
                  </span>
                </div>
                {a.description && (
                  <p className="mt-1.5 text-sm text-navy/70">{a.description}</p>
                )}
              </div>
              <div className="shrink-0 text-right text-xs text-navy/50">
                <p>{new Date(a.created_at).toLocaleString()}</p>
                <p className="mt-1 capitalize">{a.status}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
