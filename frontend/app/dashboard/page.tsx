"use client";

import { useEffect, useState } from "react";
import { reviewsApi, locationsApi, usersApi } from "@/lib/api";
import type { ReviewList, Location } from "@/types";
import StatsWidget from "@/components/StatsWidget";
import ReviewCard from "@/components/ReviewCard";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { MessageSquare, Clock, Star, RefreshCw, AlertTriangle, Sparkles, TrendingUp } from "lucide-react";
import { TrialBanner } from "@/components/TrialBanner";
import { TrialExpiredBanner } from "@/components/TrialExpiredBanner";
import { LockedButton } from "@/components/LockedButton";
import { useSubscription } from "@/hooks/useSubscription";

// SVG sparkline — rating trend over last 30 days (8 weekly buckets)
function RatingSparkline({ reviews }: { reviews: { review_date?: string | null; rating: number }[] }) {
  const buckets = 8;
  const sums: number[] = Array(buckets).fill(0);
  const counts: number[] = Array(buckets).fill(0);
  const now = Date.now();
  const span = 30 * 24 * 3600 * 1000;

  reviews.forEach((r) => {
    if (!r.review_date) return;
    const age = now - new Date(r.review_date).getTime();
    if (age < 0 || age > span) return;
    const idx = Math.min(buckets - 1, Math.floor((age / span) * buckets));
    const bucket = buckets - 1 - idx;
    sums[bucket] += r.rating;
    counts[bucket]++;
  });

  const points = sums.map((sum, i) => (counts[i] ? sum / counts[i] : null));
  const hasData = points.some((p) => p !== null);
  if (!hasData) return <p className="text-xs text-slate-600 italic">Not enough data yet</p>;

  const filled = points.map((p, i) => {
    if (p !== null) return p;
    const prev = points.slice(0, i).reverse().find((x) => x !== null);
    const next = points.slice(i + 1).find((x) => x !== null);
    return prev ?? next ?? 3;
  }) as number[];

  const W = 200, H = 56, padX = 6, padY = 6;
  const minV = 1, maxV = 5;
  const toX = (i: number) => padX + (i / (buckets - 1)) * (W - padX * 2);
  const toY = (v: number) => H - padY - ((v - minV) / (maxV - minV)) * (H - padY * 2);

  const xs = filled.map((_, i) => toX(i));
  const ys = filled.map((v) => toY(v));
  const linePath = xs.map((x, i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${ys[i].toFixed(1)}`).join(" ");
  const areaPath = linePath + ` L${xs[xs.length - 1].toFixed(1)},${H} L${xs[0].toFixed(1)},${H} Z`;

  const validRatings = points.filter((p): p is number => p !== null);
  const avgRating = validRatings.length
    ? (validRatings.reduce((a, b) => a + b, 0) / validRatings.length).toFixed(1)
    : null;

  return (
    <div className="space-y-1">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: 48 }}>
        <defs>
          <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#6366f1" stopOpacity="0.2" />
            <stop offset="100%" stopColor="#6366f1" stopOpacity="0" />
          </linearGradient>
        </defs>
        {/* Y-axis reference lines at 1★, 3★, 5★ */}
        {([1, 3, 5] as const).map((v) => (
          <g key={v}>
            <line
              x1={padX} x2={W - padX * 3}
              y1={toY(v)} y2={toY(v)}
              stroke="#2A2A3E" strokeWidth="0.5" strokeDasharray="2,3"
            />
            <text x={W - 2} y={toY(v) + 3} textAnchor="end" fontSize="6" fill="#475569">
              {v}★
            </text>
          </g>
        ))}
        {/* Area fill + line */}
        <path d={areaPath} fill="url(#sparkGrad)" />
        <path d={linePath} fill="none" stroke="#6366f1" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        {/* Data point dots for buckets with real data */}
        {points.map((p, i) =>
          p !== null ? (
            <circle key={i} cx={xs[i]} cy={ys[i]} r="2" fill="#6366f1" />
          ) : null
        )}
      </svg>
      {/* X-axis labels */}
      <div className="flex justify-between text-[10px] text-slate-600">
        <span>30d ago</span>
        {avgRating && <span className="text-indigo-400 font-medium">{avgRating}★ avg</span>}
        <span>today</span>
      </div>
    </div>
  );
}

function SentimentBar({ reviews }: { reviews: { rating: number }[] }) {
  const total = reviews.length;
  if (!total) return null;
  const pos = reviews.filter((r) => r.rating >= 4).length;
  const neu = reviews.filter((r) => r.rating === 3).length;
  const neg = reviews.filter((r) => r.rating <= 2).length;
  const pct = (n: number) => Math.round((n / total) * 100);

  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-slate-400">Sentiment breakdown</p>
      <div className="flex h-2 rounded-full overflow-hidden gap-0.5">
        {pct(pos) > 0 && <div className="bg-emerald-500 rounded-l-full" style={{ width: `${pct(pos)}%` }} title={`Positive: ${pct(pos)}%`} />}
        {pct(neu) > 0 && <div className="bg-amber-500" style={{ width: `${pct(neu)}%` }} title={`Neutral: ${pct(neu)}%`} />}
        {pct(neg) > 0 && <div className="bg-red-500 rounded-r-full" style={{ width: `${pct(neg)}%` }} title={`Negative: ${pct(neg)}%`} />}
      </div>
      <div className="flex gap-4 text-[11px] text-slate-500">
        <span><span className="text-emerald-400 font-medium">{pct(pos)}%</span> positive</span>
        <span><span className="text-amber-400 font-medium">{pct(neu)}%</span> neutral</span>
        <span><span className="text-red-400 font-medium">{pct(neg)}%</span> negative</span>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const tR = useTranslations("reviews");
  const [reviewData, setReviewData] = useState<ReviewList | null>(null);
  const [allReviews, setAllReviews] = useState<{ review_date?: string | null; rating: number; status: string }[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [loading, setLoading] = useState(true);
  const { isTrialExpired, isTrial, trialDaysRemaining } = useSubscription();
  const [hasGoogleAccount, setHasGoogleAccount] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState("");
  const [seedingDemo, setSeedingDemo] = useState(false);
  const [demoMsg, setDemoMsg] = useState("");

  useEffect(() => {
    Promise.all([
      reviewsApi.list({ limit: 10 }),
      reviewsApi.list({ limit: 200 }),
      locationsApi.list(),
      usersApi.me(),
    ])
      .then(([recent, all, locs, me]) => {
        setReviewData(recent);
        setAllReviews(all.reviews);
        setLocations(locs);
        setHasGoogleAccount(!!me.google_id);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleSeedDemo = async () => {
    setSeedingDemo(true); setDemoMsg("");
    try {
      const result = await reviewsApi.seedDemo();
      setDemoMsg(result.created > 0 ? tR("demoLoaded") : "Already loaded.");
      const [updated, all] = await Promise.all([reviewsApi.list({ limit: 10 }), reviewsApi.list({ limit: 200 })]);
      setReviewData(updated);
      setAllReviews(all.reviews);
    } catch { setDemoMsg("Failed to load demo reviews."); }
    finally { setSeedingDemo(false); }
  };

  const handleSync = async () => {
    setSyncing(true); setSyncMsg("");
    try {
      const result = await reviewsApi.sync();
      if (result.message) { setSyncMsg(result.message); }
      else {
        setSyncMsg(`Synced ${result.new_reviews ?? 0} new review(s).`);
        const [updated, all] = await Promise.all([reviewsApi.list({ limit: 10 }), reviewsApi.list({ limit: 200 })]);
        setReviewData(updated);
        setAllReviews(all.reviews);
      }
    } catch { setSyncMsg("Sync failed. Please try again."); }
    finally { setSyncing(false); }
  };

  const pending = reviewData?.reviews.filter((r) => r.status === "pending").length ?? 0;
  const total = allReviews.length || (reviewData?.total ?? 0);
  const avgRating = allReviews.length > 0
    ? allReviews.reduce((sum, r) => sum + r.rating, 0) / allReviews.length
    : 0;
  const responded = allReviews.filter((r) => r.status === "responded").length;
  const responseRate = total > 0 ? Math.round((responded / total) * 100) : 0;

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-48 bg-[#1A1A2E] rounded-lg animate-pulse" />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[0, 1, 2].map((i) => <div key={i} className="h-28 bg-[#111118] border border-[#2A2A3E] rounded-xl animate-pulse" />)}
        </div>
        <div className="space-y-3">
          {[0, 1, 2].map((i) => <div key={i} className="h-24 bg-[#111118] border border-[#2A2A3E] rounded-xl animate-pulse" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl">
      {isTrialExpired
        ? <TrialExpiredBanner />
        : isTrial && trialDaysRemaining > 0
          ? <TrialBanner daysRemaining={trialDaysRemaining} />
          : null
      }
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold text-white tracking-tight">{t("title")}</h1>
          <p className="text-slate-400 text-sm mt-1">{t("locationsConnected", { count: locations.length })}</p>
        </div>
        {hasGoogleAccount && (
          isTrialExpired ? (
            <LockedButton className="flex items-center gap-2 px-4 py-2 bg-[#1A1A2E] border border-[#2A2A3E] text-slate-300 rounded-lg text-sm font-medium">
              Sync
            </LockedButton>
          ) : (
            <button
              onClick={handleSync}
              disabled={syncing}
              className="flex items-center gap-2 px-4 py-2 bg-[#1A1A2E] border border-[#2A2A3E] hover:border-indigo-500/50 text-slate-300 hover:text-white rounded-lg text-sm font-medium transition-all disabled:opacity-50 active:scale-95"
            >
              <RefreshCw className={`w-4 h-4 ${syncing ? "animate-spin" : ""}`} />
              {syncing ? "Syncing..." : "Sync"}
            </button>
          )
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatsWidget label={t("totalReviews")} value={total} icon={MessageSquare} variant="indigo" />
        <StatsWidget label={t("pending")} value={pending} icon={Clock} variant="amber" pulse />
        <StatsWidget label={t("avgRating")} value={avgRating > 0 ? `${avgRating.toFixed(1)} ★` : "—"} icon={Star} variant="emerald" />
      </div>

      {/* Analytics section */}
      {allReviews.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Response rate */}
          <div className="bg-[#111118] border border-[#2A2A3E] rounded-xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Response rate</p>
              <span className={`text-lg font-bold ${responseRate >= 80 ? "text-emerald-400" : responseRate >= 50 ? "text-amber-400" : "text-red-400"}`}>
                {responseRate}%
              </span>
            </div>
            <div className="w-full h-2 bg-[#1A1A2E] rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-700 ${responseRate >= 80 ? "bg-emerald-500" : responseRate >= 50 ? "bg-amber-500" : "bg-red-500"}`}
                style={{ width: `${responseRate}%` }}
              />
            </div>
            <p className="text-xs text-slate-600">{responded} of {total} reviews responded</p>
          </div>

          {/* Rating trend */}
          <div className="bg-[#111118] border border-[#2A2A3E] rounded-xl p-5 space-y-2">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-3.5 h-3.5 text-indigo-400" />
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Rating trend (30d)</p>
            </div>
            <RatingSparkline reviews={allReviews} />
          </div>

          {/* Sentiment */}
          <div className="bg-[#111118] border border-[#2A2A3E] rounded-xl p-5 sm:col-span-2">
            <SentimentBar reviews={allReviews} />
          </div>
        </div>
      )}

      {/* No Google account banner */}
      {!hasGoogleAccount && (
        <div className="flex items-start gap-3 bg-amber-500/5 border border-amber-500/20 rounded-xl px-4 py-3">
          <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-medium text-amber-300">No Google account connected</p>
            <p className="text-xs text-amber-400/70 mt-0.5">
              To sync Google Business reviews, sign in with Google.{" "}
              <a href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/auth/login`} className="text-indigo-400 hover:text-indigo-300 underline font-medium">
                Connect Google account
              </a>
            </p>
          </div>
        </div>
      )}

      {syncMsg && <p className="text-xs text-slate-500 -mt-2">{syncMsg}</p>}

      {/* Recent reviews */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-white">{t("recentReviews")}</h2>
          {(reviewData?.reviews.length ?? 0) > 0 && (
            <Link href="/dashboard/reviews" className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors">View all →</Link>
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
                <button onClick={handleSync} disabled={syncing} className="text-sm text-indigo-400 hover:text-indigo-300 hover:underline disabled:opacity-50 transition-colors">
                  {syncing ? "Syncing..." : t("syncFromGoogle")}
                </button>
              )}
              <button onClick={handleSeedDemo} disabled={seedingDemo} className="flex items-center gap-1.5 text-sm text-purple-400 hover:text-purple-300 hover:underline disabled:opacity-50 transition-colors">
                <Sparkles className="w-3.5 h-3.5" />
                {seedingDemo ? tR("loadingDemo") : tR("loadDemoReviews")}
              </button>
              {demoMsg && <p className="text-xs text-slate-500">{demoMsg}</p>}
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {reviewData?.reviews.map((review) => (
              <ReviewCard key={review.id} review={review} hasGoogleAccount={hasGoogleAccount} isTrialExpired={isTrialExpired} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
