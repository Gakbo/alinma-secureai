/**
 * RiskVerdict — the platform's signature element.
 * One consistent panel everywhere a risk decision is shown:
 *   big monospace score, a gauge, the verdict, and the AI explanation
 *   in plain language (FR7: AI Explanation Engine).
 *
 * Props:
 *   score        number 0–100
 *   verdict      string  e.g. "fraud" | "suspicious" | "safe" | "high" | "medium" | "low"
 *   action       string? e.g. "Do not open the link" | "verify"
 *   explanation  string
 *   details      string[]? extra bullet points (e.g. suspicious keywords)
 */
const VERDICT_STYLES = {
  fraud: { color: "risk-high", label: "Fraud" },
  high: { color: "risk-high", label: "High risk" },
  suspicious: { color: "risk-medium", label: "Suspicious" },
  medium: { color: "risk-medium", label: "Medium risk" },
  safe: { color: "risk-low", label: "Safe" },
  low: { color: "risk-low", label: "Low risk" },
};

const BAR_COLORS = {
  "risk-high": "bg-risk-high",
  "risk-medium": "bg-risk-medium",
  "risk-low": "bg-risk-low",
};
const TEXT_COLORS = {
  "risk-high": "text-risk-high",
  "risk-medium": "text-risk-medium",
  "risk-low": "text-risk-low",
};

export default function RiskVerdict({ score, verdict, action, explanation, details = [] }) {
  const style = VERDICT_STYLES[verdict] || VERDICT_STYLES.safe;

  return (
    <div className="rounded-2xl border border-navy/10 bg-white p-6 shadow-sm">
      <div className="flex items-end justify-between gap-6">
        <div>
          <p className="text-xs uppercase tracking-widest text-navy/50">Risk score</p>
          <p className={`font-mono text-5xl font-semibold ${TEXT_COLORS[style.color]}`}>
            {Math.round(score)}
            <span className="text-2xl text-navy/40">/100</span>
          </p>
        </div>
        <div className="text-right">
          <span
            className={`inline-block rounded-full px-4 py-1.5 text-sm font-semibold text-white ${BAR_COLORS[style.color]}`}
          >
            {style.label}
          </span>
          {action && <p className="mt-2 text-sm font-medium text-navy">{action}</p>}
        </div>
      </div>

      <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-navy/10">
        <div
          className={`h-full rounded-full transition-all duration-700 ${BAR_COLORS[style.color]}`}
          style={{ width: `${Math.min(Math.max(score, 2), 100)}%` }}
        />
      </div>

      <div className="mt-5 rounded-xl bg-surface p-4">
        <p className="text-xs uppercase tracking-widest text-navy/50">Why the AI flagged this</p>
        <p className="mt-1.5 text-sm leading-relaxed text-navy">{explanation}</p>
        {details.length > 0 && (
          <ul className="mt-2 list-inside list-disc text-sm text-navy/70">
            {details.map((d, i) => (
              <li key={i}>{d}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
