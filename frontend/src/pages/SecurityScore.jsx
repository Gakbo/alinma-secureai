import { useEffect, useState } from "react";
import { getMe } from "../api.js";
import { useLanguage } from "../context/LanguageContext.jsx";
import { T } from "../i18n.js";

function ScoreRing({ score, color, size = 100 }) {
  const r = (size / 2) - 10;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - Math.min(Math.max(score, 0), 100) / 100);
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#e5e7eb" strokeWidth="8" />
      <circle
        cx={size/2} cy={size/2} r={r}
        fill="none" stroke={color} strokeWidth="8"
        strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
        style={{ transition: "stroke-dashoffset 1s cubic-bezier(.4,0,.2,1)" }}
      />
    </svg>
  );
}

function scoreLabel(score, t) {
  if (score >= 75) return { label: t.score_high,   color: "#D64545", bg: "bg-risk-high/10", text: "text-risk-high" };
  if (score >= 40) return { label: t.score_medium, color: "#E0A83C", bg: "bg-amber-50",     text: "text-risk-medium" };
  return              { label: t.score_low,    color: "#2E9E6B", bg: "bg-emerald-50",   text: "text-risk-low" };
}

function trustLabel(score, t) {
  if (score >= 75) return { label: t.score_trusted,   color: "#2E9E6B", bg: "bg-emerald-50",   text: "text-risk-low" };
  if (score >= 40) return { label: t.score_moderate,  color: "#E0A83C", bg: "bg-amber-50",     text: "text-risk-medium" };
  return              { label: t.score_low_trust, color: "#D64545", bg: "bg-risk-high/10", text: "text-risk-high" };
}

function ScoreCard({ title, subtitle, score, labelFn, icon, t }) {
  const { label, color, bg, text } = labelFn(score, t);
  return (
    <div className={`rounded-2xl border ${bg} border-navy/8 p-6 shadow-sm`}>
      <div className="flex items-center gap-3 mb-4">
        <span className="text-2xl">{icon}</span>
        <div>
          <p className="font-semibold text-navy">{title}</p>
          <p className="text-xs text-navy/50">{subtitle}</p>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <div className="relative shrink-0">
          <ScoreRing score={score} color={color} size={88} />
          <div className="absolute inset-0 flex items-center justify-center">
            <span className={`font-mono text-lg font-bold ${text}`}>{Math.round(score)}</span>
          </div>
        </div>
        <div>
          <span className={`text-sm font-bold ${text}`}>{label}</span>
          <div className="mt-2 h-1.5 w-32 overflow-hidden rounded-full bg-navy/10">
            <div className="h-full rounded-full transition-all duration-700" style={{ width: `${score}%`, backgroundColor: color }} />
          </div>
          <p className="mt-1 text-xs text-navy/50">{Math.round(score)} / 100</p>
        </div>
      </div>
    </div>
  );
}

function Recommendation({ icon, text, severity }) {
  const colors = {
    high:   "border-risk-high/20 bg-risk-high/5 text-risk-high",
    medium: "border-amber-200 bg-amber-50 text-amber-700",
    low:    "border-emerald-200 bg-emerald-50 text-emerald-700",
  };
  return (
    <div className={`flex items-start gap-3 rounded-xl border p-4 ${colors[severity]}`}>
      <span className="text-lg shrink-0">{icon}</span>
      <p className="text-sm leading-relaxed">{text}</p>
    </div>
  );
}

export default function SecurityScore() {
  const { lang, isAr } = useLanguage();
  const t = T[lang];
  const [user, setUser]   = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getMe().then(setUser).catch(() => setError(t.score_error));
  }, []);

  if (error) return (
    <div className="mx-auto max-w-3xl" dir={isAr ? "rtl" : "ltr"}>
      <h2 className="text-2xl font-bold text-navy">{t.score_title}</h2>
      <p className="mt-4 text-sm text-risk-high">{error}</p>
    </div>
  );

  if (!user) return (
    <div className="mx-auto max-w-3xl" dir={isAr ? "rtl" : "ltr"}>
      <h2 className="text-2xl font-bold text-navy">{t.score_title}</h2>
      <p className="mt-4 text-sm text-navy/50">{t.score_loading}</p>
    </div>
  );

  const overallRisk  = user.risk_score ?? 0;
  const deviceTrust  = user.device_trust_score ?? 100;
  const scamExposure = user.scam_exposure_score ?? 0;

  const overallGrade =
    overallRisk < 30 && deviceTrust > 70 && scamExposure < 30
      ? { grade: "A", label: t.score_excellent, color: "text-risk-low",    bg: "bg-emerald-50 border-emerald-200" }
      : overallRisk < 60
      ? { grade: "B", label: t.score_good,      color: "text-risk-medium", bg: "bg-amber-50 border-amber-200" }
      : { grade: "C", label: t.score_at_risk,   color: "text-risk-high",   bg: "bg-risk-high/5 border-risk-high/20" };

  const recommendations = [];
  if (deviceTrust < 60)                    recommendations.push({ icon: "📱", text: t.score_rec1,  severity: "high" });
  if (scamExposure > 50)                   recommendations.push({ icon: "📨", text: t.score_rec2,  severity: "high" });
  if (overallRisk > 60)                    recommendations.push({ icon: "🔐", text: t.score_rec3,  severity: "high" });
  if (overallRisk > 30 && overallRisk <= 60) recommendations.push({ icon: "⚠️", text: t.score_rec4, severity: "medium" });
  if (deviceTrust >= 60 && deviceTrust < 80) recommendations.push({ icon: "🛡️", text: t.score_rec5, severity: "medium" });
  if (recommendations.length === 0)        recommendations.push({ icon: "✅", text: t.score_rec_ok, severity: "low" });

  return (
    <div className="mx-auto max-w-3xl" dir={isAr ? "rtl" : "ltr"}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-navy">{t.score_title}</h2>
          <p className="mt-1 text-sm text-navy/60">{t.score_subtitle}</p>
        </div>
      </div>

      <div className={`mt-6 rounded-2xl border p-6 shadow-sm ${overallGrade.bg}`}>
        <div className="flex items-center gap-5">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-white shadow-sm">
            <span className={`font-mono text-3xl font-black ${overallGrade.color}`}>{overallGrade.grade}</span>
          </div>
          <div>
            <p className="text-xs uppercase tracking-widest text-navy/50">{t.score_grade_label}</p>
            <p className={`text-2xl font-bold ${overallGrade.color}`}>{overallGrade.label}</p>
            <p className="mt-0.5 text-sm text-navy/60">{t.score_hello}, {user.name.split(" ")[0]}. {t.score_snapshot}</p>
          </div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <ScoreCard title={t.score_behavior} subtitle={t.score_behavior_sub} score={overallRisk}  labelFn={scoreLabel} icon="🔍" t={t} />
        <ScoreCard title={t.score_device}   subtitle={t.score_device_sub}   score={deviceTrust}  labelFn={trustLabel} icon="📱" t={t} />
        <ScoreCard title={t.score_scam}     subtitle={t.score_scam_sub}     score={scamExposure} labelFn={scoreLabel} icon="🎣" t={t} />
      </div>

      <div className="mt-6 rounded-2xl border border-navy/10 bg-white p-6 shadow-sm">
        <h3 className="font-semibold text-navy mb-4 flex items-center gap-2">
          <svg className="h-4 w-4 text-copper" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          {t.score_recs}
        </h3>
        <div className="space-y-3">
          {recommendations.map((r, i) => <Recommendation key={i} {...r} />)}
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-navy/8 bg-surface p-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-navy/40 mb-2">{t.score_tips}</p>
        <ul className="space-y-1.5 text-xs text-navy/60">
          <li className="flex items-start gap-2"><span>•</span> {t.score_tip1}</li>
          <li className="flex items-start gap-2"><span>•</span> {t.score_tip2}</li>
          <li className="flex items-start gap-2"><span>•</span> {t.score_tip3}</li>
        </ul>
      </div>
    </div>
  );
}
