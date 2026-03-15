"use client";

import { useEffect, useState } from "react";
import { reviewsApi, locationsApi } from "@/lib/api";
import type { ReviewList, Location } from "@/types";
import StatsWidget from "@/components/StatsWidget";
import ReviewCard from "@/components/ReviewCard";

export default function DashboardPage() {
  const [reviewData, setReviewData] = useState<ReviewList | null>(null);
  const [locations, setLocations] = useState<Location[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      reviewsApi.list({ limit: 10 }),
      locationsApi.list(),
    ])
      .then(([reviews, locs]) => {
        setReviewData(reviews);
        setLocations(locs);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const pending = reviewData?.reviews.filter((r) => r.status === "pending").length ?? 0;
  const responded = reviewData?.reviews.filter((r) => r.status === "responded").length ?? 0;
  const total = reviewData?.total ?? 0;
  const avgRating =
    reviewData && reviewData.reviews.length > 0
      ? reviewData.reviews.reduce((sum, r) => sum + r.rating, 0) / reviewData.reviews.length
      : 0;

  if (loading) {
    return <div className="flex items-center justify-center h-64 text-gray-400">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 text-sm mt-1">
          {locations.length} location{locations.length !== 1 ? "s" : ""} connected
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatsWidget label="Total Reviews" value={total} />
        <StatsWidget label="Pending" value={pending} highlight />
        <StatsWidget label="Avg Rating" value={avgRating > 0 ? `${avgRating.toFixed(1)} ⭐` : "—"} />
      </div>

      <div>
        <h2 className="text-lg font-semibold text-gray-800 mb-3">Recent Reviews</h2>
        {reviewData?.reviews.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <p>No reviews yet.</p>
            <button
              onClick={() => reviewsApi.sync()}
              className="mt-3 text-sm text-blue-600 hover:underline"
            >
              Sync from Google
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {reviewData?.reviews.map((review) => (
              <ReviewCard key={review.id} review={review} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
