/**
 * RiskVerdict — platform signature element.
 * Props:
 *   score        number 0–100
 *   verdict      "fraud" | "suspicious" | "safe" | "high" | "medium" | "low"
 *   action       string?
 *   explanation  string
 *   details      string[]?
 */
import { useLanguage } from "../context/LanguageContext.jsx";
import { T } from "../i18n.js";

const VERDICT_CONFIG = {
  fraud:      { color: "#D64545", bg: "bg-risk-high/5",  border: "border-risk-high/20", text: "text-risk-high",   labelKey: "verdict_fraud",      icon: "🚨" },
  high:       { color: "#D64545", bg: "bg-risk-high/5",  border: "border-risk-high/20", text: "text-risk-high",   labelKey: "verdict_high",       icon: "🔴" },
  suspicious: { color: "#E0A83C", bg: "bg-amber-50",     border: "border-amber-200",    text: "text-risk-medium", labelKey: "verdict_suspicious",  icon: "⚠️" },
  medium:     { color: "#E0A83C", bg: "bg-amber-50",     border: "border-amber-200",    text: "text-risk-medium", labelKey: "verdict_medium",      icon: "🟡" },
  safe:       { color: "#2E9E6B", bg: "bg-emerald-50",   border: "border-emerald-200",  text: "text-risk-low",    labelKey: "verdict_safe",        icon: "✅" },
  low:        { color: "#2E9E6B", bg: "bg-emerald-50",   border: "border-emerald-200",  text: "text-risk-low",    labelKey: "verdict_low",         icon: "🟢" },
};

function CircleGauge({ score, color }) {
  const radius = 44;
  const circ = 2 * Math.PI * radius;
  const pct = Math.min(Math.max(score, 0), 100);
  const offset = circ * (1 - pct / 100);

  return (
    <svg width="110" height="110" viewBox="0 0 110 110" className="-rotate-90">
      <circle cx="55" cy="55" r={radius} fill="none" stroke="#e5e7eb" strokeWidth="9" />
      <circle
        cx="55" cy="55" r={radius}
        fill="none"
        stroke={color}
        strokeWidth="9"
        strokeDasharray={circ}
        strokeDashoffset={offset}
        strokeLinecap="round"
        style={{ transition: "stroke-dashoffset 0.9s cubic-bezier(.4,0,.2,1)" }}
      />
    </svg>
  );
}

export default function RiskVerdict({ score, verdict, action, explanation, details = [] }) {
  const { lang } = useLanguage();
  const s = T[lang];
  const cfg = VERDICT_CONFIG[verdict] || VERDICT_CONFIG.safe;

  return (
    <div className={`rounded-2xl border ${cfg.border} ${cfg.bg} p-6 shadow-sm`}>
      {/* Top row: gauge + score + badge */}
      <div className="flex items-center gap-6">
        <div className="relative shrink-0">
          <CircleGauge score={score} color={cfg.color} />
          <div className="absolute inset-0 flex items-center justify-center">
            <span className={`font-mono text-2xl font-bold ${cfg.text}`}>
              {Math.round(score)}
            </span>
          </div>
        </div>

        <div className="flex-1">
          <p className="text-xs uppercase tracking-widest text-navy/50">{s.verdict_score_label}</p>
          <div className="mt-1 flex items-center gap-2">
            <span className="text-lg">{cfg.icon}</span>
            <span className={`text-xl font-bold ${cfg.text}`}>{s[cfg.labelKey]}</span>
          </div>
          {action && (
            <p className="mt-2 text-sm font-medium text-navy/80 leading-snug">{action}</p>
          )}
        </div>

        <div className="hidden sm:block shrink-0 text-right">
          <span className="text-xs text-navy/40">{s.verdict_out_of}</span>
          <p className="font-mono text-3xl font-semibold text-navy/20">100</p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-navy/10">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${Math.min(Math.max(score, 2), 100)}%`, backgroundColor: cfg.color }}
        />
      </div>

      {/* AI Explanation */}
      <div className="mt-5 rounded-xl bg-white/70 border border-navy/8 p-4">
        <div className="flex items-center gap-2 mb-2">
          <svg className="h-4 w-4 text-navy/40" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          <p className="text-xs font-semibold uppercase tracking-wider text-navy/50">{s.verdict_ai}</p>
        </div>
        <p className="text-sm leading-relaxed text-navy">{explanation}</p>
        {details.length > 0 && (
          <ul className="mt-2.5 space-y-1">
            {details.map((d, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-navy/70">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-navy/30" />
                {d}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
