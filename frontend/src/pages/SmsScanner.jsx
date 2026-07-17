import { useState } from "react";
import { checkSms } from "../api.js";
import RiskVerdict from "../components/RiskVerdict.jsx";
import { useLanguage } from "../context/LanguageContext.jsx";
import { T } from "../i18n.js";

const SAMPLES = [
  {
    label: "🚨 Arabic phishing (Alinma impersonation)",
    text: "عزيزي عميل إنماء، سيتم إيقاف حسابك خلال 24 ساعة. يرجى تحديث بياناتك فوراً عبر الرابط: http://alinma-verify.xyz/update",
  },
  {
    label: "🚨 English phishing (suspension threat)",
    text: "Dear Alinma customer, your account will be suspended due to suspicious activity. Verify now: http://secure-alinma.net/verify?token=8a2f",
  },
  {
    label: "🚨 Prize scam (Arabic)",
    text: "تهانينا! لقد فزت بجائزة إنماء الكبرى بقيمة 10,000 ريال. أدخل بيانات حسابك البنكي هنا لاستلام الجائزة: http://win.alinma-prize.com",
  },
  {
    label: "✅ Legitimate transaction SMS",
    text: "Alinma: SAR 250.00 spent on card ending 4321 at Panda, Riyadh. Balance SAR 12,340.",
  },
];

export default function SmsScanner() {
  const { lang } = useLanguage();
  const s = T[lang];

  const ACTION = {
    fraud:      s.sms_action_fraud,
    suspicious: s.sms_action_suspicious,
    safe:       s.sms_action_safe,
  };

  const [message, setMessage] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showSamples, setShowSamples] = useState(false);

  async function handleCheck() {
    setError("");
    setLoading(true);
    setResult(null);
    try {
      setResult(await checkSms(message));
    } catch {
      setError(s.sms_error);
    } finally {
      setLoading(false);
    }
  }

  function useSample(text) {
    setMessage(text);
    setResult(null);
    setShowSamples(false);
  }

  return (
    <div className="mx-auto max-w-3xl">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-navy">{s.sms_title}</h2>
          <p className="mt-1 text-sm text-navy/60">{s.sms_subtitle}</p>
        </div>
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-copper/10 text-copper">
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
        </div>
      </div>

      {/* Input card */}
      <div className="mt-6 rounded-2xl border border-navy/10 bg-white p-6 shadow-sm">
        <label className="block text-sm font-semibold text-navy mb-2">{s.sms_label}</label>
        <textarea
          dir="auto"
          rows={5}
          value={message}
          onChange={(e) => { setMessage(e.target.value); setResult(null); }}
          placeholder={s.sms_placeholder}
          className="w-full resize-none rounded-xl border border-navy/15 bg-surface px-4 py-3 text-sm outline-none transition focus:border-copper focus:ring-1 focus:ring-copper/30"
        />

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            onClick={handleCheck}
            disabled={loading || !message.trim()}
            className="flex items-center gap-2 rounded-xl bg-copper px-6 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-copper-600 disabled:opacity-40"
          >
            {loading ? (
              <>
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                {s.sms_analyzing}
              </>
            ) : (
              <>
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                {s.sms_analyze}
              </>
            )}
          </button>

          <div className="relative">
            <button
              onClick={() => setShowSamples(!showSamples)}
              className="rounded-xl border border-navy/15 bg-white px-4 py-2.5 text-sm text-navy/60 transition hover:bg-surface hover:text-navy"
            >
              {s.sms_demo} ▾
            </button>
            {showSamples && (
              <div className="absolute top-full left-0 z-10 mt-1 w-80 rounded-xl border border-navy/10 bg-white shadow-lg">
                {SAMPLES.map((sample, i) => (
                  <button
                    key={i}
                    onClick={() => useSample(sample.text)}
                    className="block w-full px-4 py-3 text-left text-xs hover:bg-surface border-b border-navy/5 last:border-0 first:rounded-t-xl last:rounded-b-xl"
                  >
                    <span className="font-medium text-navy">{sample.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {message && (
            <button
              onClick={() => { setMessage(""); setResult(null); }}
              className="text-xs text-navy/40 hover:text-navy/70"
            >
              {s.sms_clear}
            </button>
          )}
        </div>

        {error && (
          <p className="mt-3 flex items-center gap-2 text-sm text-risk-high">
            <span>⚠️</span> {error}
          </p>
        )}
      </div>

      {/* Result */}
      {result && (
        <div className="mt-6">
          <RiskVerdict
            score={result.risk_score}
            verdict={result.classification}
            action={ACTION[result.classification]}
            explanation={result.explanation}
            details={[
              ...(result.suspicious_keywords?.length
                ? [`Suspicious phrasing detected: ${result.suspicious_keywords.join(", ")}`]
                : []),
              ...(result.contains_suspicious_url
                ? ["Contains an unrecognized or shortened URL"]
                : []),
            ]}
          />
        </div>
      )}
    </div>
  );
}
