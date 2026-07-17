import axios from "axios";

// In dev, Vite proxies /api -> http://127.0.0.1:8000 (see vite.config.js).
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && window.location.pathname !== "/login") {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

// ---------------------------------------------------------------------------
// JWT helpers (no library needed — just base64-decode the payload segment)
// ---------------------------------------------------------------------------
export function getTokenPayload() {
  const token = localStorage.getItem("token");
  if (!token) return null;
  try {
    return JSON.parse(atob(token.split(".")[1]));
  } catch {
    return null;
  }
}

export function getTokenRole() {
  return getTokenPayload()?.role || "customer";
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------
export async function login(email, password) {
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);
  const { data } = await api.post("/auth/login", form);
  localStorage.setItem("token", data.access_token);
  return data;
}

export async function register(name, email, phone, password) {
  const { data } = await api.post("/auth/register", { name, email, phone, password });
  localStorage.setItem("token", data.access_token);
  return data;
}

export async function getMe() {
  return (await api.get("/auth/me")).data;
}

export async function forgotPassword(email) {
  return (await api.post("/auth/forgot-password", { email })).data;
}

export async function resetPassword(token, new_password) {
  return (await api.post("/auth/reset-password", { token, new_password })).data;
}

// ---------------------------------------------------------------------------
// SMS
// ---------------------------------------------------------------------------
export async function checkSms(message) {
  return (await api.post("/sms/check", { message })).data;
}

// ---------------------------------------------------------------------------
// Transactions
// ---------------------------------------------------------------------------
export async function checkTransaction(payload) {
  return (await api.post("/transactions/check", payload)).data;
}

// ---------------------------------------------------------------------------
// Alerts
// ---------------------------------------------------------------------------
export async function getAlerts() {
  return (await api.get("/alerts/")).data;
}

export async function updateAlertStatus(alertId, status) {
  return (await api.patch(`/alerts/${alertId}`, { status })).data;
}

export async function acknowledgeAlert(alertId) {
  return (await api.post(`/alerts/${alertId}/acknowledge`)).data;
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------
export async function getDashboardSummary() {
  return (await api.get("/dashboard/summary")).data;
}

export async function getHighRiskUsers() {
  return (await api.get("/dashboard/high-risk-users")).data;
}

export async function getFraudTrend() {
  return (await api.get("/dashboard/fraud-trend")).data;
}

export async function getRegionStats() {
  return (await api.get("/dashboard/region-stats")).data;
}

// ---------------------------------------------------------------------------
// Admin
// ---------------------------------------------------------------------------
export async function getAdminUsers() {
  return (await api.get("/admin/users")).data;
}

export async function updateUserRole(userId, role) {
  return (await api.patch(`/admin/users/${userId}/role`, { role })).data;
}

// ---------------------------------------------------------------------------
// AI Chat Assistant
// ---------------------------------------------------------------------------
export async function sendChatMessage(messages, lang = "en") {
  return (await api.post("/chat/message", { messages, lang })).data;
}

export default api;
