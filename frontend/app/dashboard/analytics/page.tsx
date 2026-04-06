"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BarChart2, Lock } from "lucide-react";

interface AnalyticsData {
  total_reviews: number;
  reviews_last_30_days: number;
  reviews_last_7_days: number;
  average_rating: number | null;
  response_rate: number;
  pending_reviews: number;
  rating_distribution: Record<string, number>;
  reviews_by_day: { date: string; count: number }[];
}

function SkeletonCard() {
  return (
    <div className="bg-[#111118] border border-[#2A2A3E] rounded-xl p-5 animate-pulse">
      <div className="h-3 w-24 bg-[#1A1A2E] rounded mb-4" />
      <div className="h-8 w-16 bg-[#1A1A2E] rounded" />
    </div>
  );
}

function KpiCard({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="bg-[#111118] border border-[#2A2A3E] rounded-xl p-5 space-y-1">
      <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">{label}</p>
      <p className="text-2xl font-bold text-white">{value}</p>
    </div>
  );
}

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [upgradeRequired, setUpgradeRequired] = useState(false);

  useEffect(() => {
    const token =
      typeof window !== "undefined" ? localStorage.getItem("air_token") : "";
    const base =
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    fetch(`${base}/analytics`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (res) => {
        if (res.status === 402) {
          setUpgradeRequired(true);
          return;
        }
        if (!res.ok) throw new Error("Failed to load analytics");
        setData(await res.json());
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="space-y-6 max-w-5xl">
        <div className="h-8 w-40 bg-[#1A1A2E] rounded-lg animate-pulse" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
        <div className="h-48 bg-[#111118] border border-[#2A2A3E] rounded-xl animate-pulse" />
        <div className="h-48 bg-[#111118] border border-[#2A2A3E] rounded-xl animate-pulse" />
      </div>
    );
  }

  if (upgradeRequired) {
    return (
      <div className="max-w-5xl">
        <div className="flex flex-col items-center justify-center py-24 text-center space-y-5">
          <div className="w-14 h-14 bg-[#1A1A2E] border border-[#2A2A3E] rounded-xl flex items-center justify-center">
            <Lock className="w-6 h-6 text-slate-500" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Analytics is a Pro feature</h2>
            <p className="text-sm text-slate-400 mt-1 max-w-sm">
              Upgrade to Pro or Agency to unlock detailed analytics, rating
              distributions, and review trends.
            </p>
          </div>
          <Link
            href="/dashboard/billing"
            className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg transition-colors"
          >
            Upgrade now
          </Link>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const maxRatingCount = Math.max(
    ...Object.values(data.rating_distribution).map(Number),
    1
  );
  const maxDayCount = Math.max(
    ...data.reviews_by_day.map((d) => d.count),
    1
  );

  const stars = (n: number) => "⭐".repeat(n);

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-center gap-3">
        <BarChart2 className="w-5 h-5 text-indigo-400" />
        <h1 className="text-2xl font-semibold text-white tracking-tight">Analytics</h1>
      </div>

      {/* KPI grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <KpiCard label="Total Reviews" value={data.total_reviews} />
        <KpiCard label="Last 30 Days" value={data.reviews_last_30_days} />
        <KpiCard label="Last 7 Days" value={data.reviews_last_7_days} />
        <KpiCard
          label="Average Rating"
          value={
            data.average_rating !== null
              ? `${data.average_rating.toFixed(1)} ⭐`
              : "—"
          }
        />
        <KpiCard label="Response Rate" value={`${data.response_rate}%`} />
        <KpiCard label="Pending Reviews" value={data.pending_reviews} />
      </div>

      {/* Rating distribution */}
      <div className="bg-[#111118] border border-[#2A2A3E] rounded-xl p-5 space-y-4">
        <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
          Rating Distribution
        </p>
        <div className="space-y-3">
          {[5, 4, 3, 2, 1].map((star) => {
            const count = data.rating_distribution[String(star)] ?? 0;
            const pct =
              maxRatingCount > 0 ? (count / maxRatingCount) * 100 : 0;
            return (
              <div key={star} className="flex items-center gap-3">
                <span className="text-xs text-slate-400 w-[90px] shrink-0">
                  {stars(star)}
                </span>
                <div className="flex-1 h-2 bg-[#1A1A2E] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-teal-500 rounded-full transition-all duration-500"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="text-xs text-slate-400 w-6 text-right shrink-0">
                  {count}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Reviews by day */}
      <div className="bg-[#111118] border border-[#2A2A3E] rounded-xl p-5 space-y-4">
        <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
          Reviews per Day (last 30 days)
        </p>
        {data.reviews_by_day.length === 0 ? (
          <p className="text-sm text-slate-600 italic">
            No reviews in the last 30 days.
          </p>
        ) : (
          <div className="flex items-end gap-0.5 h-16">
            {data.reviews_by_day.map((d, i) => (
              <div
                key={i}
                className="flex-1 bg-teal-500 rounded-t-sm min-h-[2px] opacity-80 hover:opacity-100 transition-opacity"
                style={{
                  height: `${(d.count / maxDayCount) * 100}%`,
                }}
                title={`${d.date}: ${d.count} review${d.count !== 1 ? "s" : ""}`}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
