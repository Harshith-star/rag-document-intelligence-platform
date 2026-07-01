import axios from "axios";

const api = axios.create({ baseURL: `${import.meta.env.VITE_API_URL}/api/v1`, });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ── auth ──────────────────────────────────────────────────────────────────
export const register = (email, password, full_name) =>
  api.post("/auth/register", { email, password, full_name });

export const login = (email, password) => {
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);
  return api.post("/auth/login", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
};

export const getMe    = ()          => api.get("/auth/me");
export const updateMe = (full_name) => api.put("/auth/me", { full_name });

// ── documents ─────────────────────────────────────────────────────────────
export const uploadDocument = (file, onProgress) => {
  const form = new FormData();
  form.append("file", file);
  return api.post("/documents/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (e) => onProgress && onProgress(Math.round((e.loaded * 100) / e.total)),
  });
};

export const listDocuments   = (page = 1, limit = 10, search = "") =>
  api.get("/documents/", { params: { page, limit, search: search || undefined } });
export const renameDocument  = (id, filename) => api.patch(`/documents/${id}`, { filename });
export const deleteDocument  = (id)           => api.delete(`/documents/${id}`);

// ── QA ────────────────────────────────────────────────────────────────────
export const askQuestion = (question) => api.post("/qa/ask", { question });

// ── analytics ─────────────────────────────────────────────────────────────
export const getDashboardStats = () => api.get("/dashboard/stats");

export default api;
