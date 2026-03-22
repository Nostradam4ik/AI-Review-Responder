"use client";

import { useEffect, useState } from "react";
import { reviewsApi, locationsApi, usersApi } from "@/lib/api";
import type { ReviewList, Location } from "@/types";
import StatsWidget from "@/components/StatsWidget";
import ReviewCard from "@/components/ReviewCard";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { MessageSquare, Clock, Star, RefreshCw, AlertTriangle, Sparkles } from "lucide-react";

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const tR = useTranslations("reviews");
  const [reviewData, setReviewData] = useState<ReviewList | null>(null);
  const [locations, setLocations] = useState<Location[]>([]);
  const [loading, setLoading] = useState(true);
  const [hasGoogleAccount, setHasGoogleAccount] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState("");
  const [seedingDemo, setSeedingDemo] = useState(false);
  const [demoMsg, setDemoMsg] = useState("");

  useEffect(() => {
    Promise.all([
      reviewsApi.list({ limit: 10 }),
      locationsApi.list(),
      usersApi.me(),
    ])
      .then(([reviews, locs, me]) => {
        setReviewData(reviews);
        setLocations(locs);
        setHasGoogleAccount(!!me.google_id);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleSeedDemo = async () => {
    setSeedingDemo(true);
    setDemoMsg("");
    try {
      const result = await reviewsApi.seedDemo();
      setDemoMsg(result.created > 0 ? tR("demoLoaded") : "Already loaded.");
      const updated = await reviewsApi.list({ limit: 10 });
      setReviewData(updated);
    } catch {
      setDemoMsg("Failed to load demo reviews.");
    } finally {
      setSeedingDemo(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setSyncMsg("");
    try {
      const result = await reviewsApi.sync();
      if (result.message) {
        setSyncMsg(result.message);
      } else {
        setSyncMsg(`Synced ${result.new_reviews ?? 0} new review(s).`);
        const updated = await reviewsApi.list({ limit: 10 });
        setReviewData(updated);
      }
    } catch {
      setSyncMsg("Sync failed. Please try again.");
    } finally {
      setSyncing(false);
    }
  };

  const pending = reviewData?.reviews.filter((r) => r.status === "pending").length ?? 0;
  const total = reviewData?.total ?? 0;
  const avgRating =
    reviewData && reviewData.reviews.length > 0
      ? reviewData.reviews.reduce((sum, r) => sum + r.rating, 0) / reviewData.reviews.length
      : 0;

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-48 bg-[#1A1A2E] rounded-lg animate-pulse" />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-28 bg-[#111118] border border-[#2A2A3E] rounded-xl animate-pulse" />
          ))}
        </div>
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-24 bg-[#111118] border border-[#2A2A3E] rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold text-white tracking-tight">{t("title")}</h1>
          <p className="text-slate-400 text-sm mt-1">
            {t("locationsConnected", { count: locations.length })}
          </p>
        </div>
        {hasGoogleAccount && (
          <button
            onClick={handleSync}
            disabled={syncing}
            className="flex items-center gap-2 px-4 py-2 bg-[#1A1A2E] border border-[#2A2A3E] hover:border-indigo-500/50 text-slate-300 hover:text-white rounded-lg text-sm font-medium transition-all duration-150 disabled:opacity-50 active:scale-95"
          >
            <RefreshCw className={`w-4 h-4 ${syncing ? "animate-spin" : ""}`} />
            {syncing ? "Syncing..." : "Sync"}
          </button>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatsWidget
          label={t("totalReviews")}
          value={total}
          icon={MessageSquare}
          variant="indigo"
        />
        <StatsWidget
          label={t("pending")}
          value={pending}
          icon={Clock}
          variant="amber"
          pulse
        />
        <StatsWidget
          label={t("avgRating")}
          value={avgRating > 0 ? `${avgRating.toFixed(1)} ★` : "—"}
          icon={Star}
          variant="emerald"
        />
      </div>

      {/* No Google account banner */}
      {!hasGoogleAccount && (
        <div className="flex items-start gap-3 bg-amber-500/5 border border-amber-500/20 rounded-xl px-4 py-3">
          <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-medium text-amber-300">No Google account connected</p>
            <p className="text-xs text-amber-400/70 mt-0.5">
              To sync Google Business reviews, sign in with Google.{" "}
              <a
                href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/auth/login`}
                className="text-indigo-400 hover:text-indigo-300 underline font-medium"
              >
                Connect Google account
              </a>
            </p>
          </div>
        </div>
      )}

      {syncMsg && (
        <p className="text-xs text-slate-500 -mt-2">{syncMsg}</p>
      )}

      {/* Recent reviews */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-white">{t("recentReviews")}</h2>
          {(reviewData?.reviews.length ?? 0) > 0 && (
            <Link
              href="/dashboard/reviews"
              className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
            >
              View all →
            </Link>
          )}
        </div>

        {reviewData?.reviews.length === 0 ? (
          <div className="text-center py-16 space-y-4">
            <div className="w-16 h-16 mx-auto opacity-10">
              <MessageSquare className="w-full h-full text-slate-400" />
            </div>
            <p className="text-slate-400 text-sm">{t("noReviews")}</p>
            <div className="flex flex-col items-center gap-2">
              {hasGoogleAccount && (
                <button
                  onClick={handleSync}
                  disabled={syncing}
                  className="text-sm text-indigo-400 hover:text-indigo-300 hover:underline disabled:opacity-50 transition-colors"
                >
                  {syncing ? "Syncing..." : t("syncFromGoogle")}
                </button>
              )}
              <button
                onClick={handleSeedDemo}
                disabled={seedingDemo}
                className="flex items-center gap-1.5 text-sm text-purple-400 hover:text-purple-300 hover:underline disabled:opacity-50 transition-colors"
              >
                <Sparkles className="w-3.5 h-3.5" />
                {seedingDemo ? tR("loadingDemo") : tR("loadDemoReviews")}
              </button>
              {demoMsg && <p className="text-xs text-slate-500">{demoMsg}</p>}
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {reviewData?.reviews.map((review) => (
              <ReviewCard key={review.id} review={review} hasGoogleAccount={hasGoogleAccount} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
