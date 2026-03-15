export interface User {
  id: string;
  email: string;
  business_name: string | null;
  tone_preference: "formal" | "warm" | "casual";
  language: string;
  plan: string;
  created_at: string;
}

export interface Location {
  id: string;
  gmb_location_id: string;
  name: string;
  address: string | null;
  is_active: boolean;
}

export type ReviewStatus = "pending" | "responded" | "ignored";

export interface Review {
  id: string;
  location_id: string;
  gmb_review_id: string;
  author_name: string | null;
  rating: number;
  comment: string | null;
  language: string | null;
  review_date: string | null;
  status: ReviewStatus;
  synced_at: string;
}

export interface ReviewList {
  reviews: Review[];
  total: number;
}

export type Tone = "formal" | "warm" | "casual";

export interface Response {
  id: string;
  review_id: string;
  ai_draft: string;
  final_text: string | null;
  tone_used: string | null;
  model_used: string | null;
  was_edited: boolean;
  published_at: string | null;
  created_at: string;
}
