import { useState } from "react";
import { checkSms } from "../api.js";
import RiskVerdict from "../components/RiskVerdict.jsx";

const SAMPLE =
  "Dear Alinma customer, your account will be blocked. Click here immediately: http://alinma-verify.xyz";

export default function SmsScanner() {
  const [message, setMessage] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleCheck() {
    setError("");
    setLoading(true);
    setResult(null);
    try {
      setResult(await checkSms(message));
    } catch {
      setError("The message could not be analyzed. Check that the backend is running and try again.");
    } finally {
      setLoading(false);
    }
  }

  const actionFor = {
    fraud: "Do not open any link in this message",
    suspicious: "Treat with caution — verify through the official Alinma app",
    safe: "No action needed",
  };

  return (
    <div className="mx-auto max-w-3xl">
      <h2 className="text-2xl font-semibold">SMS Scanner</h2>
      <p className="mt-1 text-sm text-navy/60">
        Paste a suspicious SMS (Arabic or English). The AI classifies it and explains why.
      </p>

      <div className="mt-6 rounded-2xl border border-navy/10 bg-white p-6 shadow-sm">
        <textarea
          dir="auto"
          rows={4}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Paste the SMS text here…"
          className="w-full resize-none rounded-lg border border-navy/20 px-3 py-2.5 outline-none focus:border-copper"
        />
        <div className="mt-3 flex items-center gap-3">
          <button
            onClick={handleCheck}
            disabled={loading || !message.trim()}
            className="rounded-lg bg-copper px-5 py-2.5 font-semibold text-white transition hover:bg-copper-600 disabled:opacity-50"
          >
            {loading ? "Analyzing…" : "Analyze message"}
          </button>
          <button
            onClick={() => setMessage(SAMPLE)}
            className="text-sm text-navy/60 underline-offset-2 hover:underline"
          >
            Use demo phishing sample
          </button>
        </div>
        {error && <p className="mt-3 text-sm text-risk-high">{error}</p>}
      </div>

      {result && (
        <div className="mt-6">
          <RiskVerdict
            score={result.risk_score}
            verdict={result.classification}
            action={actionFor[result.classification]}
            explanation={result.explanation}
            details={[
              ...(result.suspicious_keywords?.length
                ? [`Suspicious phrasing: ${result.suspicious_keywords.join(", ")}`]
                : []),
              ...(result.contains_suspicious_url ? ["Contains an unrecognized or shortened link"] : []),
            ]}
          />
        </div>
      )}
    </div>
  );
}
