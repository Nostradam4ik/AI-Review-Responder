"use client";

import { useEffect, useState, useCallback } from "react";
import { reviewsApi } from "@/lib/api";
import type { Review, ReviewStatus } from "@/types";
import ReviewCard from "@/components/ReviewCard";
import { useTranslations } from "next-intl";

export default function ReviewsPage() {
  const t = useTranslations("reviews");
  const [reviews, setReviews] = useState<Review[]>([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState<ReviewStatus | "all">("all");
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  const STATUS_FILTERS: { label: string; value: ReviewStatus | "all" }[] = [
    { label: t("all"), value: "all" },
    { label: t("pending"), value: "pending" },
    { label: t("responded"), value: "responded" },
    { label: t("ignored"), value: "ignored" },
  ];

  const fetchReviews = useCallback(async () => {
    setLoading(true);
    try {
      const data = await reviewsApi.list({
        status: status === "all" ? undefined : status,
        limit: 50,
      });
      setReviews(data.reviews);
      setTotal(data.total);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [status]);

  useEffect(() => { fetchReviews(); }, [fetchReviews]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await reviewsApi.sync();
      await fetchReviews();
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-zinc-100">{t("title")}</h1>
          <p className="text-gray-500 dark:text-zinc-400 text-sm mt-1">{t("total", { count: total })}</p>
        </div>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition"
        >
          {syncing ? t("syncing") : t("syncButton")}
        </button>
      </div>

      <div className="flex gap-2">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setStatus(f.value)}
            className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
              status === f.value
                ? "bg-blue-600 text-white"
                : "bg-white dark:bg-zinc-900 text-gray-600 dark:text-zinc-400 border border-gray-200 dark:border-zinc-700 hover:bg-gray-50 dark:hover:bg-zinc-800"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400 dark:text-zinc-500">{t("loading")}</div>
      ) : reviews.length === 0 ? (
        <div className="text-center py-12 text-gray-400 dark:text-zinc-500">{t("noReviews")}</div>
      ) : (
        <div className="space-y-4">
          {reviews.map((review) => (
            <ReviewCard key={review.id} review={review} onStatusChange={fetchReviews} />
          ))}
        </div>
      )}
    </div>
  );
}
