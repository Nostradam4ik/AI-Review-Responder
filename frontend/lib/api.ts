import axios from "axios";
import { getToken, logout } from "./auth";
import type { Location, Review, ReviewList, Response, Tone } from "@/types";

export interface BillingStatus {
  subscription: {
    status: string;
    plan_id?: string;
    trial_end?: string;
    current_period_end?: string;
  };
  plan: {
    id: string;
    name: string;
    price_eur: number;
    max_locations: number;
    max_responses_per_month: number;
    features: Record<string, boolean>;
  } | null;
  usage: {
    responses_this_month: number;
    responses_limit: number;
  };
}

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 → logout
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      logout();
    }
    return Promise.reject(err);
  }
);

// --- Locations ---
export const locationsApi = {
  list: () => api.get<Location[]>("/locations/").then((r) => r.data),
  sync: () => api.post("/locations/sync").then((r) => r.data),
};

// --- Reviews ---
export const reviewsApi = {
  list: (params?: { status?: string; location_id?: string; limit?: number; offset?: number; date_from?: string; date_to?: string }) =>
    api.get<ReviewList>("/reviews/", { params }).then((r) => r.data),
  sync: (location_id?: string) =>
    api.post("/reviews/sync", null, { params: { location_id } }).then((r) => r.data),
  seedDemo: () => api.post("/reviews/seed-demo").then((r) => r.data),
  exportCsv: (params?: { status?: string; date_from?: string; date_to?: string }) => {
    const token = typeof window !== "undefined" ? localStorage.getItem("air_token") : "";
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.date_from) qs.set("date_from", params.date_from);
    if (params?.date_to) qs.set("date_to", params.date_to);
    const url = `${base}/reviews/export/csv${qs.toString() ? "?" + qs.toString() : ""}`;
    const a = document.createElement("a");
    a.href = url;
    // Can't set auth header via anchor — use fetch + blob instead
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.blob())
      .then((blob) => {
        const blobUrl = URL.createObjectURL(blob);
        a.href = blobUrl;
        a.download = "reviews.csv";
        a.click();
        URL.revokeObjectURL(blobUrl);
      });
  },
  testTelegram: () =>
    fetch("/api/test-telegram", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${typeof window !== "undefined" ? (localStorage.getItem("air_token") || "") : ""}`,
      },
    }).then((r) => r.json()),
  updateStatus: (id: string, status: string) =>
    api.patch(`/reviews/${id}/status`, null, { params: { status } }).then((r) => r.data),
};

// --- Responses ---
export const responsesApi = {
  generate: (review_id: string, tone: Tone) =>
    api.post<Response>("/responses/generate", { review_id, tone }).then((r) => r.data),
  edit: (response_id: string, final_text: string) =>
    api.put<Response>(`/responses/${response_id}`, { final_text }).then((r) => r.data),
  publish: (response_id: string) =>
    api.post<Response>(`/responses/${response_id}/publish`).then((r) => r.data),
  getForReview: (review_id: string) =>
    api.get<Response | null>(`/responses/review/${review_id}`).then((r) => r.data),
};

// --- Users ---
const _token = () =>
  typeof window !== "undefined" ? (localStorage.getItem("air_token") || "") : "";

export const usersApi = {
  me: () => api.get("/users/me").then((r) => r.data),
  update: (data: { business_name?: string; tone_preference?: string; language?: string; onboarding_done?: boolean; auto_publish?: boolean; response_instructions?: string }) =>
    api.patch("/users/me", data).then((r) => r.data),
  changePassword: (current_password: string, new_password: string) =>
    api.post("/users/me/change-password", { current_password, new_password }).then((r) => r.data),
  telegramStatus: () =>
    fetch("/api/telegram-status", {
      headers: { Authorization: `Bearer ${_token()}` },
    }).then((r) => r.json()) as Promise<{ connected: boolean }>,
  telegramDisconnect: () =>
    api.delete("/users/me/telegram").then((r) => r.data),
};

// --- Billing ---
export const billingApi = {
  status: () => api.get<BillingStatus>("/billing/status").then((r) => r.data),
  checkout: (plan_id: string) =>
    api.post<{ checkout_url: string }>("/billing/checkout", { plan_id }).then((r) => r.data),
  portal: () => api.post<{ portal_url: string }>("/billing/portal").then((r) => r.data),
};

export default api;
