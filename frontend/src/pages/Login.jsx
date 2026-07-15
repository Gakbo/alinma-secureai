import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../api.js";

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit() {
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/");
    } catch {
      setError("Email or password is incorrect. Check your details and try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-navy px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center text-white">
          <p className="font-mono text-xs uppercase tracking-widest text-copper">Alinma</p>
          <h1 className="text-3xl font-semibold">SecureAI</h1>
          <p className="mt-2 text-sm text-white/60">
            AI-powered fraud prevention for Alinma Bank
          </p>
        </div>
        <div className="rounded-2xl bg-white p-8 shadow-xl">
          <label className="block text-sm font-medium">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="mt-1.5 w-full rounded-lg border border-navy/20 px-3 py-2.5 outline-none focus:border-copper"
          />
          <label className="mt-4 block text-sm font-medium">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            className="mt-1.5 w-full rounded-lg border border-navy/20 px-3 py-2.5 outline-none focus:border-copper"
          />
          {error && <p className="mt-3 text-sm text-risk-high">{error}</p>}
          <button
            onClick={handleSubmit}
            disabled={loading || !email || !password}
            className="mt-6 w-full rounded-lg bg-copper py-2.5 font-semibold text-white transition hover:bg-copper-600 disabled:opacity-50"
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
          <p className="mt-4 text-center text-xs text-navy/50">
            Demo accounts are created by <code>seed_data.py</code> — see the backend README.
          </p>
        </div>
      </div>
    </div>
  );
}
