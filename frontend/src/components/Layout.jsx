import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { getMe } from "../api.js";

const nav = [
  { to: "/sms", label: "SMS Scanner", hint: "Check a suspicious message" },
  { to: "/transactions", label: "Transfer Guardian", hint: "Score a transaction" },
  { to: "/alerts", label: "Fraud Alerts", hint: "Alert history" },
  { to: "/dashboard", label: "Analyst Dashboard", hint: "Live fraud analytics", analystOnly: true },
];

export default function Layout() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);

  useEffect(() => {
    getMe().then(setUser).catch(() => {});
  }, []);

  const isAnalyst = user && ["analyst", "admin"].includes(user.role);

  function logout() {
    localStorage.removeItem("token");
    navigate("/login");
  }

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-64 shrink-0 flex-col bg-navy text-white">
        <div className="border-b border-white/10 px-6 py-5">
          <p className="font-mono text-xs uppercase tracking-widest text-copper">Alinma</p>
          <h1 className="text-lg font-semibold">SecureAI</h1>
          <p className="mt-1 text-xs text-white/60">Fraud Prevention Platform</p>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-4">
          {nav
            .filter((n) => !n.analystOnly || isAnalyst)
            .map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                className={({ isActive }) =>
                  `block rounded-lg px-3 py-2.5 transition ${
                    isActive ? "bg-copper text-white" : "text-white/75 hover:bg-white/10"
                  }`
                }
              >
                <span className="block text-sm font-medium">{n.label}</span>
                <span className="block text-xs opacity-70">{n.hint}</span>
              </NavLink>
            ))}
        </nav>
        <div className="border-t border-white/10 px-6 py-4 text-sm">
          {user && (
            <>
              <p className="font-medium">{user.name}</p>
              <p className="text-xs capitalize text-white/60">{user.role}</p>
            </>
          )}
          <button onClick={logout} className="mt-2 text-xs text-copper hover:underline">
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 px-8 py-8">
        <Outlet context={{ user }} />
      </main>
    </div>
  );
}
