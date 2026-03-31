"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { reviewsApi, usersApi, billingApi } from "@/lib/api";
import type { Review, ReviewStatus } from "@/types";
import ReviewCard from "@/components/ReviewCard";
import { useTranslations } from "next-intl";
import { RefreshCw, MessageSquare, Sparkles, Download, Search, X, Lock } from "lucide-react";
import UpgradeModal from "@/components/UpgradeModal";

type DateRange = "all" | "today" | "week" | "month" | "3months";

function getDateBounds(range: DateRange): { date_from?: string; date_to?: string } {
  if (range === "all") return {};
  const now = new Date();
  const to = now.toISOString();
  let from: Date;
  if (range === "today") {
    from = new Date(now); from.setHours(0, 0, 0, 0);
  } else if (range === "week") {
    from = new Date(now); from.setDate(now.getDate() - 7);
  } else if (range === "month") {
    from = new Date(now); from.setMonth(now.getMonth() - 1);
  } else {
    from = new Date(now); from.setMonth(now.getMonth() - 3);
  }
  return { date_from: from.toISOString(), date_to: to };
}

const DATE_RANGES: { label: string; value: DateRange }[] = [
  { label: "All time", value: "all" },
  { label: "Today", value: "today" },
  { label: "This week", value: "week" },
  { label: "This month", value: "month" },
  { label: "Last 3 months", value: "3months" },
];

export default function ReviewsPage() {
  const t = useTranslations("reviews");
  const [reviews, setReviews] = useState<Review[]>([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState<ReviewStatus | "all">("all");
  const [dateRange, setDateRange] = useState<DateRange>("all");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [hasGoogleAccount, setHasGoogleAccount] = useState(false);
  const [seedingDemo, setSeedingDemo] = useState(false);
  const [demoMsg, setDemoMsg] = useState("");
  const [canCsvExport, setCanCsvExport] = useState(true);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);

  const STATUS_FILTERS: { label: string; value: ReviewStatus | "all" }[] = [
    { label: t("all"), value: "all" },
    { label: t("pending"), value: "pending" },
    { label: t("responded"), value: "responded" },
    { label: t("ignored"), value: "ignored" },
  ];

  const fetchReviews = useCallback(async () => {
    setLoading(true);
    try {
      const bounds = getDateBounds(dateRange);
      const data = await reviewsApi.list({
        status: status === "all" ? undefined : status,
        limit: 200,
        ...bounds,
      });
      setReviews(data.reviews);
      setTotal(data.total);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [status, dateRange]);

  useEffect(() => {
    usersApi.me().then((me) => setHasGoogleAccount(!!me.google_id)).catch(() => {});
    billingApi.status().then((s) => {
      const isTrial = s.subscription?.status === "trialing";
      const trialActive = isTrial && s.subscription?.trial_end
        ? new Date(s.subscription.trial_end) > new Date()
        : false;
      const hasCsv = s.plan?.features?.export_csv === true;
      setCanCsvExport(trialActive || hasCsv);
    }).catch(() => {});
    fetchReviews();
  }, [fetchReviews]);

  const filtered = useMemo(() => {
    if (!search.trim()) return reviews;
    const q = search.toLowerCase();
    return reviews.filter(
      (r) => r.author_name?.toLowerCase().includes(q) || r.comment?.toLowerCase().includes(q)
    );
  }, [reviews, search]);

  const handleSync = async () => {
    setSyncing(true);
    try { await reviewsApi.sync(); await fetchReviews(); }
    finally { setSyncing(false); }
  };

  const handleSeedDemo = async () => {
    setSeedingDemo(true); setDemoMsg("");
    try {
      const result = await reviewsApi.seedDemo();
      setDemoMsg(result.created > 0 ? t("demoLoaded") : "Already loaded.");
      await fetchReviews();
    } catch { setDemoMsg("Failed to load demo reviews."); }
    finally { setSeedingDemo(false); }
  };

  const handleExportCsv = () => {
    if (!canCsvExport) {
      setShowUpgradeModal(true);
      return;
    }
    const bounds = getDateBounds(dateRange);
    reviewsApi.exportCsv({ status: status === "all" ? undefined : status, ...bounds });
  };

  return (
    <div className="space-y-5 max-w-4xl">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold text-white tracking-tight">{t("title")}</h1>
          <p className="text-slate-400 text-sm mt-1">
            {search ? `${filtered.length} of ${total}` : total} {total === 1 ? "review" : "reviews"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleExportCsv}
            title={canCsvExport ? "Export CSV" : "Pro feature — upgrade to export"}
            className="flex items-center gap-1.5 px-3 py-2 border border-[#2A2A3E] hover:border-indigo-500/40 text-slate-400 hover:text-white rounded-lg text-xs font-medium transition-all active:scale-95"
          >
            {canCsvExport ? (
              <Download className="w-3.5 h-3.5" />
            ) : (
              <Lock className="w-3.5 h-3.5" />
            )}
            CSV
          </button>
          {hasGoogleAccount && (
            <button
              onClick={handleSync}
              disabled={syncing}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-all disabled:opacity-50 active:scale-95"
            >
              <RefreshCw className={`w-4 h-4 ${syncing ? "animate-spin" : ""}`} />
              {syncing ? t("syncing") : t("syncButton")}
            </button>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-3">
        <div className="flex gap-2 flex-wrap">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setStatus(f.value)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all active:scale-95 ${
                status === f.value
                  ? "bg-indigo-600 text-white"
                  : "bg-[#1A1A2E] text-slate-400 hover:text-white border border-[#2A2A3E] hover:border-indigo-500/30"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex gap-1 flex-wrap">
            {DATE_RANGES.map((d) => (
              <button
                key={d.value}
                onClick={() => setDateRange(d.value)}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                  dateRange === d.value
                    ? "bg-[#2A2A3E] text-white border border-indigo-500/30"
                    : "text-slate-500 hover:text-slate-300"
                }`}
              >
                {d.label}
              </button>
            ))}
          </div>

          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name or text…"
              className="w-full pl-9 pr-8 py-1.5 rounded-lg border border-[#2A2A3E] bg-[#0A0A0F] text-sm text-white placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
            />
            {search && (
              <button onClick={() => setSearch("")} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300">
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-28 bg-[#111118] border border-[#2A2A3E] rounded-xl animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 space-y-4">
          <div className="w-16 h-16 mx-auto opacity-10">
            <MessageSquare className="w-full h-full text-slate-400" />
          </div>
          <p className="text-xl font-semibold text-white">{t("noReviews")}</p>
          <p className="text-slate-500 text-sm">
            {search ? "No reviews match your search." : status !== "all" ? "Try a different filter." : "Start by syncing or loading demo data."}
          </p>
          {status === "all" && !search && (
            <div className="flex flex-col items-center gap-2 mt-2">
              <button
                onClick={handleSeedDemo}
                disabled={seedingDemo}
                className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-all disabled:opacity-50 active:scale-95"
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
          {filtered.map((review) => (
            <ReviewCard
              key={review.id}
              review={review}
              hasGoogleAccount={hasGoogleAccount}
              onStatusChange={fetchReviews}
            />
          ))}
        </div>
      )}
      {showUpgradeModal && (
        <UpgradeModal feature="CSV export" onClose={() => setShowUpgradeModal(false)} />
      )}
    </div>
  );
}
