import axios from "axios";
import { getToken, logout } from "./auth";
import type { Location, Review, ReviewList, Response, Tone } from "@/types";

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
  list: (params?: { status?: string; location_id?: string; limit?: number; offset?: number }) =>
    api.get<ReviewList>("/reviews/", { params }).then((r) => r.data),
  sync: (location_id?: string) =>
    api.post("/reviews/sync", null, { params: { location_id } }).then((r) => r.data),
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

export default api;
