import axios from "axios";
import { getToken, setToken, logout } from "./auth";
import type { CollectionLink, Location, ReviewList, Response, Tone } from "@/types";

export interface UserProfile {
  id: string;
  email: string;
  business_name: string | null;
  tone_preference: string;
  language: string;
  email_verified: boolean;
  onboarding_done: boolean;
  has_password: boolean;
  telegram_connected: boolean;
  auto_publish: boolean;
  response_instructions: string | null;
  is_admin: boolean;
}

export interface AdminStats {
  total_users: number;
  active_subscriptions: number;
  trial_users: number;
  expired_trials: number;
  mrr: number;
  new_users_today: number;
  new_users_this_week: number;
}

export interface AdminUser {
  id: string;
  email: string;
  name: string | null;
  avatar_url: string | null;
  plan_name: string;
  subscription_status: string;
  is_trial: boolean;
  trial_days_remaining: number | null;
  trial_end: string | null;
  subscription_start: string | null;
  subscription_end: string | null;
  ai_responses_limit: number | null;
  created_at: string;
  last_seen_at: string | null;
  locations_count: number;
  reviews_count: number;
  responses_count: number;
  is_admin: boolean;
}

export interface AdminUserList {
  users: AdminUser[];
  total: number;
  page: number;
  pages: number;
}

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
    ai_responses_limit?: number | null;
  };
  is_trial?: boolean;
  is_trial_expired?: boolean;
  trial_days_remaining?: number | null;
  pro_features_available?: boolean;
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

// Handle 401 (try refresh first) → logout, 402 → redirect to billing
let _refreshing: Promise<string | null> | null = null;

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config;
    if (err.response?.status === 401 && !original._retried) {
      original._retried = true;
      if (!_refreshing) {
        _refreshing = axios
          .post(
            `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/auth/refresh`,
            null,
            { withCredentials: true },
          )
          .then((r) => {
            setToken(r.data.access_token);
            return r.data.access_token as string;
          })
          .catch(() => null)
          .finally(() => { _refreshing = null; });
      }
      const newToken = await _refreshing;
      if (newToken) {
        original.headers.Authorization = `Bearer ${newToken}`;
        return api(original);
      }
      logout();
    } else if (err.response?.status === 402) {
      const detail = err.response?.data?.detail || "upgrade_required";
      if (typeof window !== "undefined") {
        window.location.href = `/dashboard/billing?reason=${detail}`;
      }
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
  list: (params?: { status?: string; location_id?: string; limit?: number; offset?: number; date_from?: string; date_to?: string; sort?: string }) =>
    api.get<ReviewList>("/reviews/", { params }).then((r) => r.data),
  sync: (location_id?: string) =>
    api.post("/reviews/sync", null, { params: { location_id } }).then((r) => r.data),
  seedDemo: () => api.post("/reviews/seed-demo").then((r) => r.data),
  exportCsv: (params?: { status?: string; location_id?: string; date_from?: string; date_to?: string }) => {
    const token = typeof window !== "undefined" ? localStorage.getItem("air_token") : "";
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.location_id) qs.set("location_id", params.location_id);
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
        a.download = `reviews_${new Date().toISOString().split("T")[0]}.csv`;
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
    api.patch(`/reviews/${id}/status`, { status }).then((r) => r.data),
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
  me: () => api.get<UserProfile>("/users/me").then((r) => r.data),
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

// --- Admin ---
export const adminApi = {
  stats: () => api.get<AdminStats>("/admin/stats").then((r) => r.data),
  users: (params: { search?: string; status?: string; page?: number; limit?: number }) =>
    api.get<AdminUserList>("/admin/users", { params }).then((r) => r.data),
  resetTrial: (userId: string, days = 14) =>
    api.post(`/admin/users/${userId}/reset-trial`, { days }).then((r) => r.data),
  changePlan: (userId: string, plan: string, reason = "") =>
    api.post(`/admin/users/${userId}/change-plan`, { plan, reason }).then((r) => r.data),
  deleteUser: (userId: string) =>
    api.delete(`/admin/users/${userId}`).then((r) => r.data),
  editUser: (userId: string, body: {
    plan?: string;
    status?: string;
    subscription_start?: string | null;
    subscription_end?: string | null;
    trial_end?: string | null;
    ai_responses_limit?: number | null;
  }) => api.put(`/admin/users/${userId}`, body).then((r) => r.data),
};

// --- Billing ---
export const billingApi = {
  status: () => api.get<BillingStatus>("/billing/status").then((r) => r.data),
  checkout: (plan_id: string) =>
    api.post<{ checkout_url: string }>("/billing/checkout", { plan_id }).then((r) => r.data),
  portal: () => api.post<{ portal_url: string }>("/billing/portal").then((r) => r.data),
};

// --- Collection Links ---
export const collectionApi = {
  create: (location_id: string, google_maps_url: string) =>
    api.post<CollectionLink>("/collection/links", { location_id, google_maps_url }).then((r) => r.data),
  list: () =>
    api.get<{ links: CollectionLink[] }>("/collection/links").then((r) => r.data),
  stats: (link_id: string) =>
    api.get<{ link_id: string; total_submissions: number; avg_rating: number; by_rating: Record<string, number> }>(
      `/collection/links/${link_id}/stats`
    ).then((r) => r.data),
};

export default api;
