"use client";

import { useEffect, useState, useCallback } from "react";
import { reviewsApi, usersApi } from "@/lib/api";
import type { Review, ReviewStatus } from "@/types";
import ReviewCard from "@/components/ReviewCard";
import { useTranslations } from "next-intl";
import { RefreshCw, MessageSquare, Sparkles } from "lucide-react";

export default function ReviewsPage() {
  const t = useTranslations("reviews");
  const [reviews, setReviews] = useState<Review[]>([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState<ReviewStatus | "all">("all");
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [hasGoogleAccount, setHasGoogleAccount] = useState(false);
  const [seedingDemo, setSeedingDemo] = useState(false);
  const [demoMsg, setDemoMsg] = useState("");

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

  useEffect(() => {
    usersApi.me().then((me) => setHasGoogleAccount(!!me.google_id)).catch(() => {});
    fetchReviews();
  }, [fetchReviews]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await reviewsApi.sync();
      await fetchReviews();
    } finally {
      setSyncing(false);
    }
  };

  const handleSeedDemo = async () => {
    setSeedingDemo(true);
    setDemoMsg("");
    try {
      const result = await reviewsApi.seedDemo();
      setDemoMsg(result.created > 0 ? t("demoLoaded") : "Already loaded.");
      await fetchReviews();
    } catch {
      setDemoMsg("Failed to load demo reviews.");
    } finally {
      setSeedingDemo(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold text-white tracking-tight">{t("title")}</h1>
          <p className="text-slate-400 text-sm mt-1">
            {total} {total === 1 ? "review" : "reviews"} au total
          </p>
        </div>
        {hasGoogleAccount && (
          <button
            onClick={handleSync}
            disabled={syncing}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-all duration-150 disabled:opacity-50 active:scale-95"
          >
            <RefreshCw className={`w-4 h-4 ${syncing ? "animate-spin" : ""}`} />
            {syncing ? t("syncing") : t("syncButton")}
          </button>
        )}
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 flex-wrap">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setStatus(f.value)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-150 active:scale-95 ${
              status === f.value
                ? "bg-indigo-600 text-white"
                : "bg-[#1A1A2E] text-slate-400 hover:text-white border border-[#2A2A3E] hover:border-indigo-500/30"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-28 bg-[#111118] border border-[#2A2A3E] rounded-xl animate-pulse" />
          ))}
        </div>
      ) : reviews.length === 0 ? (
        <div className="text-center py-20 space-y-4">
          <div className="w-16 h-16 mx-auto opacity-10">
            <MessageSquare className="w-full h-full text-slate-400" />
          </div>
          <p className="text-xl font-semibold text-white">{t("noReviews")}</p>
          <p className="text-slate-500 text-sm">
            {status !== "all" ? "Try a different filter." : "Start by syncing or loading demo data."}
          </p>
          {status === "all" && (
            <div className="flex flex-col items-center gap-2 mt-2">
              <button
                onClick={handleSeedDemo}
                disabled={seedingDemo}
                className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-all duration-150 disabled:opacity-50 active:scale-95"
              >
                <Sparkles className="w-4 h-4" />
                {seedingDemo ? t("loadingDemo") : t("loadDemoReviews")}
              </button>
              {demoMsg && <p className="text-xs text-slate-500 mt-1">{demoMsg}</p>}
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {reviews.map((review) => (
            <ReviewCard
              key={review.id}
              review={review}
              hasGoogleAccount={hasGoogleAccount}
              onStatusChange={fetchReviews}
            />
          ))}
        </div>
      )}
    </div>
  );
}
