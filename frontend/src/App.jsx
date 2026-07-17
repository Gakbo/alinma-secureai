import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import Login from "./pages/Login.jsx";
import Signup from "./pages/Signup.jsx";
import ForgotPassword from "./pages/ForgotPassword.jsx";
import ResetPassword from "./pages/ResetPassword.jsx";
import SmsScanner from "./pages/SmsScanner.jsx";
import TransactionChecker from "./pages/TransactionChecker.jsx";
import Alerts from "./pages/Alerts.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import SecurityScore from "./pages/SecurityScore.jsx";
import AdminPanel from "./pages/AdminPanel.jsx";
import { getTokenRole } from "./api.js";

// Redirect to login if no token
function RequireAuth({ children }) {
  const token = localStorage.getItem("token");
  return token ? children : <Navigate to="/login" replace />;
}

// Redirect to /sms if the user's role is not in the allowed list
function RequireRole({ roles, children }) {
  const token = localStorage.getItem("token");
  if (!token) return <Navigate to="/login" replace />;
  const role = getTokenRole();
  if (!roles.includes(role)) return <Navigate to="/sms" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login"           element={<Login />} />
      <Route path="/signup"          element={<Signup />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password"  element={<ResetPassword />} />

      <Route
        path="/"
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        {/* Root → role-aware landing */}
        <Route index element={<RoleRedirect />} />

        {/* Customer + Analyst + Admin */}
        <Route path="sms"          element={<SmsScanner />} />
        <Route path="transactions" element={<TransactionChecker />} />

        {/* Customer only */}
        <Route path="score" element={<SecurityScore />} />

        {/* Analyst + Admin + Customer */}
        <Route
          path="alerts"
          element={
            <RequireRole roles={["analyst", "admin", "customer"]}>
              <Alerts />
            </RequireRole>
          }
        />
        <Route
          path="dashboard"
          element={
            <RequireRole roles={["analyst", "admin"]}>
              <Dashboard />
            </RequireRole>
          }
        />

        {/* Admin only */}
        <Route
          path="admin"
          element={
            <RequireRole roles={["admin"]}>
              <AdminPanel />
            </RequireRole>
          }
        />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

// Sends the user to the right page based on their JWT role
function RoleRedirect() {
  const role = getTokenRole();
  if (role === "admin")   return <Navigate to="/admin"     replace />;
  if (role === "analyst") return <Navigate to="/dashboard" replace />;
  return <Navigate to="/sms" replace />;
}
