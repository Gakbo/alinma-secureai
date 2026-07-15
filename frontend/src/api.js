import axios from "axios";

// In dev, Vite proxies /api -> http://127.0.0.1:8000 (see vite.config.js).
// In Docker/production, set VITE_API_URL to the backend's public URL.
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

export async function login(email, password) {
  // FastAPI's OAuth2PasswordRequestForm expects form fields username/password.
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);
  const { data } = await api.post("/auth/login", form);
  localStorage.setItem("token", data.access_token);
  return data;
}

export async function getMe() {
  return (await api.get("/auth/me")).data;
}

export async function checkSms(message) {
  return (await api.post("/sms/check", { message })).data;
}

export async function checkTransaction(payload) {
  return (await api.post("/transactions/check", payload)).data;
}

export async function getAlerts() {
  return (await api.get("/alerts/")).data;
}

export async function getDashboardSummary() {
  return (await api.get("/dashboard/summary")).data;
}

export async function getHighRiskUsers() {
  return (await api.get("/dashboard/high-risk-users")).data;
}

export default api;
