import { useState } from "react";
import { checkTransaction } from "../api.js";
import RiskVerdict from "../components/RiskVerdict.jsx";

const COUNTRIES = ["SA", "AE", "PK", "IN", "EG", "UK", "US", "NG"];

export default function TransactionChecker() {
  const [form, setForm] = useState({
    amount: "",
    recipient: "",
    is_new_recipient: false,
    country: "SA",
  });
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function loadDemo() {
    setForm({ amount: "20000", recipient: "New Beneficiary LLC", is_new_recipient: true, country: "PK" });
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
      setError("The transaction could not be scored. Check that the backend is running and try again.");
    } finally {
      setLoading(false);
    }
  }

  const actionLabel = {
    approve: "Approve — matches normal behavior",
    verify: "Additional verification required before sending",
    reject: "Recommend blocking this transfer",
  };

  return (
    <div className="mx-auto max-w-3xl">
      <h2 className="text-2xl font-semibold">Transfer Guardian</h2>
      <p className="mt-1 text-sm text-navy/60">
        Score a transfer before the money leaves the account.
      </p>

      <div className="mt-6 rounded-2xl border border-navy/10 bg-white p-6 shadow-sm">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium">Amount (SAR)</label>
            <input
              type="number"
              min="0"
              value={form.amount}
              onChange={(e) => update("amount", e.target.value)}
              className="mt-1.5 w-full rounded-lg border border-navy/20 px-3 py-2.5 outline-none focus:border-copper"
            />
          </div>
          <div>
            <label className="block text-sm font-medium">Recipient</label>
            <input
              value={form.recipient}
              onChange={(e) => update("recipient", e.target.value)}
              className="mt-1.5 w-full rounded-lg border border-navy/20 px-3 py-2.5 outline-none focus:border-copper"
            />
          </div>
          <div>
            <label className="block text-sm font-medium">Destination country</label>
            <select
              value={form.country}
              onChange={(e) => update("country", e.target.value)}
              className="mt-1.5 w-full rounded-lg border border-navy/20 bg-white px-3 py-2.5 outline-none focus:border-copper"
            >
              {COUNTRIES.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </div>
          <label className="flex items-end gap-2 pb-2.5 text-sm font-medium">
            <input
              type="checkbox"
              checked={form.is_new_recipient}
              onChange={(e) => update("is_new_recipient", e.target.checked)}
              className="h-4 w-4 accent-copper"
            />
            First transfer to this recipient
          </label>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <button
            onClick={handleCheck}
            disabled={loading || !form.amount || !form.recipient.trim()}
            className="rounded-lg bg-copper px-5 py-2.5 font-semibold text-white transition hover:bg-copper-600 disabled:opacity-50"
          >
            {loading ? "Scoring…" : "Score transfer"}
          </button>
          <button onClick={loadDemo} className="text-sm text-navy/60 underline-offset-2 hover:underline">
            Use demo high-risk transfer
          </button>
        </div>
        {error && <p className="mt-3 text-sm text-risk-high">{error}</p>}
      </div>

      {result && (
        <div className="mt-6">
          <RiskVerdict
            score={result.risk_score * 100}
            verdict={result.risk_level}
            action={actionLabel[result.recommended_action]}
            explanation={result.explanation}
          />
        </div>
      )}
    </div>
  );
}
