import { useState } from "react";
import { checkTransaction } from "../api.js";
import RiskVerdict from "../components/RiskVerdict.jsx";
import { useLanguage } from "../context/LanguageContext.jsx";
import { T } from "../i18n.js";

const COUNTRIES = [
  { code: "SA", label: "🇸🇦 Saudi Arabia" },
  { code: "AE", label: "🇦🇪 United Arab Emirates" },
  { code: "EG", label: "🇪🇬 Egypt" },
  { code: "JO", label: "🇯🇴 Jordan" },
  { code: "KW", label: "🇰🇼 Kuwait" },
  { code: "BH", label: "🇧🇭 Bahrain" },
  { code: "QA", label: "🇶🇦 Qatar" },
  { code: "OM", label: "🇴🇲 Oman" },
  { code: "PK", label: "🇵🇰 Pakistan" },
  { code: "IN", label: "🇮🇳 India" },
  { code: "UK", label: "🇬🇧 United Kingdom" },
  { code: "US", label: "🇺🇸 United States" },
  { code: "NG", label: "🇳🇬 Nigeria" },
  { code: "PH", label: "🇵🇭 Philippines" },
];

const DEMO_SCENARIOS = [
  {
    label: "🔴 High risk — large foreign transfer",
    form: { amount: "20000", recipient: "New Beneficiary LLC", is_new_recipient: true, country: "NG" },
  },
  {
    label: "🟡 Medium risk — new recipient abroad",
    form: { amount: "4500", recipient: "FastPay Services", is_new_recipient: true, country: "PK" },
  },
  {
    label: "🟢 Low risk — routine domestic",
    form: { amount: "800", recipient: "Ahmed Al-Zahrani", is_new_recipient: false, country: "SA" },
  },
];

export default function TransactionChecker() {
  const { lang } = useLanguage();
  const s = T[lang];

  const ACTION_LABEL = {
    approve: s.transfer_action_approve,
    verify:  s.transfer_action_verify,
    reject:  s.transfer_action_reject,
  };

  const [form, setForm] = useState({
    amount: "",
    recipient: "",
    is_new_recipient: false,
    country: "SA",
  });
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showScenarios, setShowScenarios] = useState(false);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
    setResult(null);
  }

  function loadScenario(f) {
    setForm(f);
    setResult(null);
    setShowScenarios(false);
  }

  async function handleCheck() {
    setError("");
    setLoading(true);
    setResult(null);
    try {
      setResult(
        await checkTransaction({
          amount: parseFloat(form.amount),
          recipient: form.recipient,
          is_new_recipient: form.is_new_recipient,
          country: form.country,
        })
      );
    } catch {
      setError(s.transfer_error);
    } finally {
      setLoading(false);
    }
  }

  const formValid = form.amount && parseFloat(form.amount) > 0 && form.recipient.trim();

  return (
    <div className="mx-auto max-w-3xl">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-navy">{s.transfer_title}</h2>
          <p className="mt-1 text-sm text-navy/60">{s.transfer_subtitle}</p>
        </div>
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-copper/10 text-copper">
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
          </svg>
        </div>
      </div>

      {/* Form */}
      <div className="mt-6 rounded-2xl border border-navy/10 bg-white p-6 shadow-sm">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-semibold text-navy">{s.transfer_amount}</label>
            <div className="relative mt-1.5">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm font-medium text-navy/40">SAR</span>
              <input
                type="number"
                min="0"
                value={form.amount}
                onChange={(e) => update("amount", e.target.value)}
                className="w-full rounded-xl border border-navy/15 bg-surface py-2.5 pl-12 pr-4 text-sm outline-none transition focus:border-copper focus:ring-1 focus:ring-copper/30"
                placeholder="0.00"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-semibold text-navy">{s.transfer_recipient}</label>
            <input
              value={form.recipient}
              onChange={(e) => update("recipient", e.target.value)}
              className="mt-1.5 w-full rounded-xl border border-navy/15 bg-surface px-4 py-2.5 text-sm outline-none transition focus:border-copper focus:ring-1 focus:ring-copper/30"
              placeholder={s.transfer_rec_ph}
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-navy">{s.transfer_country}</label>
            <select
              value={form.country}
              onChange={(e) => update("country", e.target.value)}
              className="mt-1.5 w-full rounded-xl border border-navy/15 bg-surface px-4 py-2.5 text-sm outline-none transition focus:border-copper focus:ring-1 focus:ring-copper/30"
            >
              {COUNTRIES.map((c) => (
                <option key={c.code} value={c.code}>{c.label}</option>
              ))}
            </select>
          </div>

          <div className="flex items-end pb-1">
            <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-navy/15 bg-surface px-4 py-2.5 w-full transition hover:border-copper/40">
              <input
                type="checkbox"
                checked={form.is_new_recipient}
                onChange={(e) => update("is_new_recipient", e.target.checked)}
                className="h-4 w-4 rounded accent-copper"
              />
              <span className="text-sm font-medium text-navy">{s.transfer_new_recip}</span>
            </label>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <button
            onClick={handleCheck}
            disabled={loading || !formValid}
            className="flex items-center gap-2 rounded-xl bg-copper px-6 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-copper-600 disabled:opacity-40"
          >
            {loading ? (
              <>
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                {s.transfer_scoring}
              </>
            ) : (
              <>
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {s.transfer_score}
              </>
            )}
          </button>

          <div className="relative">
            <button
              onClick={() => setShowScenarios(!showScenarios)}
              className="rounded-xl border border-navy/15 bg-white px-4 py-2.5 text-sm text-navy/60 transition hover:bg-surface hover:text-navy"
            >
              {s.transfer_demo} ▾
            </button>
            {showScenarios && (
              <div className="absolute top-full left-0 z-10 mt-1 w-72 rounded-xl border border-navy/10 bg-white shadow-lg">
                {DEMO_SCENARIOS.map((sc, i) => (
                  <button
                    key={i}
                    onClick={() => loadScenario(sc.form)}
                    className="block w-full px-4 py-3 text-left text-xs font-medium text-navy hover:bg-surface border-b border-navy/5 last:border-0 first:rounded-t-xl last:rounded-b-xl"
                  >
                    {sc.label}
                  </button>
                ))}
              </div>
            )}
          </div>
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
            score={result.risk_score * 100}
            verdict={result.risk_level}
            action={ACTION_LABEL[result.recommended_action]}
            explanation={result.explanation}
          />
        </div>
      )}
    </div>
  );
}
