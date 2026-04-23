"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Brain, Download, Lock, AlertTriangle, TrendingDown, TrendingUp, Minus, Lightbulb, CheckCircle2 } from "lucide-react";
import { locationsApi } from "@/lib/api";
import type { Location } from "@/types";

// ── Types ────────────────────────────────────────────────────────────────────

interface Complaint {
  category: string;
  mention_count: number;
  percentage: number;
  severity: "high" | "medium" | "low";
  trend: "worsening" | "stable" | "improving";
  example_quotes: string[];
  root_cause?: string;
  recommendation?: string;
  impact?: string;
}

interface Praise {
  category: string;
  mention_count: number;
  percentage: number;
  example_quotes: string[];
  recommendation?: string;
}

interface ActionItem {
  priority: number;
  action: string;
  effort: string;
  expected_impact: string;
  timeframe: string;
}

interface Analysis {
  business_type: string;
  overall_sentiment: string;
  avg_rating: number;
  nps_estimate: number;
  summary: string;
  complaints: Complaint[];
  praises: Praise[];
  urgent_alerts: string[];
  opportunities: string[];
  comparison: { vs_previous_period: string; response_rate: string };
  action_plan: ActionItem[];
}

interface Meta {
  business_name: string;
  location_name: string;
  period_label: string;
  total_reviews: number;
  response_rate: number;
  generated_at: string;
}

// ── Demo data (shown blurred to free plan users) ──────────────────────────────

const DEMO_ANALYSIS: Analysis = {
  business_type: "restaurant",
  overall_sentiment: "mixed",
  avg_rating: 3.8,
  nps_estimate: 12,
  summary:
    "This period showed mixed customer sentiment with notable concerns around service speed during peak hours. Food quality remains a strong differentiator but staffing issues are impacting the overall experience. Immediate action on service delays could recover approximately 0.4★ in average rating.",
  complaints: [
    {
      category: "Service Speed",
      mention_count: 12,
      percentage: 28,
      severity: "high",
      trend: "worsening",
      example_quotes: ["waited 45 min", "staff ignored us", "too slow"],
      root_cause: "Understaffed during peak hours (12-2pm, 7-9pm)",
      recommendation: "Hire 2 part-time staff for lunch and dinner rush",
      impact: "Fixing this could improve avg rating by ~0.4★",
    },
    {
      category: "Cleanliness",
      mention_count: 6,
      percentage: 14,
      severity: "medium",
      trend: "stable",
      example_quotes: ["tables not cleaned quickly", "floors needed attention"],
      recommendation: "Add a dedicated floor manager during service hours",
    },
  ],
  praises: [
    {
      category: "Food Quality",
      mention_count: 18,
      percentage: 43,
      example_quotes: ["pasta was incredible", "best pizza in town", "fresh ingredients"],
      recommendation: "Leverage in marketing — highlight signature dishes on social media",
    },
    {
      category: "Ambience",
      mention_count: 10,
      percentage: 24,
      example_quotes: ["love the vibe", "romantic setting", "great music"],
      recommendation: "Feature in Google Business photos and booking platforms",
    },
  ],
  urgent_alerts: [],
  opportunities: [
    "15 customers asked about delivery — consider adding delivery service",
    "8 reviews mentioned interest in private dining for groups",
  ],
  comparison: {
    vs_previous_period: "Rating dropped from 4.1 to 3.8 (-0.3★)",
    response_rate: "You responded to 68% of reviews (industry avg: 45%)",
  },
  action_plan: [
    {
      priority: 1,
      action: "Address service speed during peak hours",
      effort: "medium",
      expected_impact: "high",
      timeframe: "2 weeks",
    },
    {
      priority: 2,
      action: "Respond to all unanswered 1-2★ reviews",
      effort: "low",
      expected_impact: "medium",
      timeframe: "this week",
    },
  ],
};

const DEMO_META: Meta = {
  business_name: "Le Petit Bistro",
  location_name: "Paris, 15ème",
  period_label: "Sample Period",
  total_reviews: 42,
  response_rate: 68,
  generated_at: "April 14, 2026",
};

// ── Sub-components ────────────────────────────────────────────────────────────

function SkeletonCard({ h = "h-24" }: { h?: string }) {
  return <div className={`bg-[#111118] border border-[#2A2A3E] rounded-xl ${h} animate-pulse`} />;
}

function KpiBox({ label, value, valueColor }: { label: string; value: React.ReactNode; valueColor?: string }) {
  return (
    <div className="bg-[#111118] border border-[#2A2A3E] rounded-xl p-4 text-center">
      <p className={`text-2xl font-bold ${valueColor ?? "text-white"}`}>{value}</p>
      <p className="text-[11px] text-slate-500 uppercase tracking-wider mt-1">{label}</p>
    </div>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    high: "bg-red-500/10 text-red-400 border-red-500/30",
    medium: "bg-amber-500/10 text-amber-400 border-amber-500/30",
    low: "bg-slate-500/10 text-slate-400 border-slate-500/30",
  };
  return (
    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${colors[severity] ?? colors.low}`}>
      {severity.toUpperCase()}
    </span>
  );
}

function TrendIcon({ trend }: { trend: string }) {
  if (trend === "worsening") return <TrendingDown className="w-3.5 h-3.5 text-red-400 inline mr-1" />;
  if (trend === "improving") return <TrendingUp className="w-3.5 h-3.5 text-green-400 inline mr-1" />;
  return <Minus className="w-3.5 h-3.5 text-slate-400 inline mr-1" />;
}

function ProgressBar({ pct, color = "bg-indigo-500" }: { pct: number; color?: string }) {
  return (
    <div className="w-full h-1.5 bg-[#1A1A2E] rounded-full overflow-hidden mt-2 mb-3">
      <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(100, pct)}%` }} />
    </div>
  );
}

function ComplaintCard({ item, index }: { item: Complaint; index: number }) {
  return (
    <div className="bg-[#111118] border border-[#2A2A3E] border-l-2 border-l-red-500 rounded-xl p-4 space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-xs font-bold text-indigo-400">#{index + 1}</span>
        <span className="font-semibold text-white flex-1">{item.category}</span>
        <span className="text-sm font-bold text-white">{item.percentage}%</span>
      </div>
      <ProgressBar pct={item.percentage} color="bg-red-500" />
      <div className="flex gap-2 flex-wrap">
        <SeverityBadge severity={item.severity} />
        <span className="text-[10px] text-slate-400 flex items-center">
          <TrendIcon trend={item.trend} />{item.trend.charAt(0).toUpperCase() + item.trend.slice(1)}
        </span>
      </div>
      {item.root_cause && (
        <p className="text-xs text-slate-400"><strong className="text-slate-300">Root cause:</strong> {item.root_cause}</p>
      )}
      {item.recommendation && (
        <p className="text-xs text-indigo-400 font-medium">→ {item.recommendation}</p>
      )}
      {item.impact && (
        <p className="text-xs text-green-400">📈 {item.impact}</p>
      )}
      {item.example_quotes.length > 0 && (
        <p className="text-xs text-slate-500 italic">
          {item.example_quotes.slice(0, 3).map((q, i) => (
            <span key={i}>{i > 0 && " · "}&ldquo;{q}&rdquo;</span>
          ))}
        </p>
      )}
    </div>
  );
}

function PraiseCard({ item, index }: { item: Praise; index: number }) {
  return (
    <div className="bg-[#111118] border border-[#2A2A3E] border-l-2 border-l-green-500 rounded-xl p-4 space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-xs font-bold text-indigo-400">#{index + 1}</span>
        <span className="font-semibold text-white flex-1">{item.category}</span>
        <span className="text-sm font-bold text-white">{item.percentage}%</span>
      </div>
      <ProgressBar pct={item.percentage} color="bg-green-500" />
      {item.recommendation && (
        <p className="text-xs text-green-400 font-medium">→ {item.recommendation}</p>
      )}
      {item.example_quotes.length > 0 && (
        <p className="text-xs text-slate-500 italic">
          {item.example_quotes.slice(0, 3).map((q, i) => (
            <span key={i}>{i > 0 && " · "}&ldquo;{q}&rdquo;</span>
          ))}
        </p>
      )}
    </div>
  );
}

function ActionCard({ item }: { item: ActionItem }) {
  return (
    <div className="bg-[#111118] border border-[#2A2A3E] rounded-xl p-4">
      <p className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider mb-1">Priority {item.priority}</p>
      <p className="font-semibold text-white mb-2">✦ {item.action}</p>
      <div className="flex gap-4 text-xs text-slate-400 flex-wrap">
        <span>Effort: <strong className="text-slate-300">{item.effort}</strong></span>
        <span>Impact: <strong className="text-slate-300">{item.expected_impact}</strong></span>
        <span>Timeframe: <strong className="text-slate-300">{item.timeframe}</strong></span>
      </div>
    </div>
  );
}

// ── Report view ───────────────────────────────────────────────────────────────

function ReportView({ analysis, meta }: { analysis: Analysis; meta: Meta }) {
  const npsDisplay = analysis.nps_estimate >= 0 ? `+${analysis.nps_estimate}` : String(analysis.nps_estimate);
  return (
    <div className="space-y-6">
      {/* KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <KpiBox label="Reviews" value={meta.total_reviews} />
        <KpiBox label="Avg Rating" value={`${analysis.avg_rating.toFixed(1)}★`} />
        <KpiBox
          label="Response Rate"
          value={`${meta.response_rate.toFixed(1)}%`}
          valueColor={
            meta.response_rate >= 30
              ? "text-emerald-400"
              : meta.response_rate > 0
              ? "text-amber-400"
              : "text-red-400"
          }
        />
        <KpiBox label="NPS Estimate" value={npsDisplay} />
      </div>

      {/* Summary */}
      <div className="bg-[#111118] border border-[#2A2A3E] border-l-2 border-l-indigo-500 rounded-xl p-4">
        <p className="text-sm text-slate-300 leading-relaxed">{analysis.summary}</p>
      </div>

      {/* Urgent alerts */}
      {analysis.urgent_alerts.length > 0 && (
        <div className="bg-red-500/5 border border-red-500/30 rounded-xl p-4 space-y-2">
          <div className="flex items-center gap-2 text-red-400 font-semibold text-sm">
            <AlertTriangle className="w-4 h-4" /> Urgent Alerts
          </div>
          {analysis.urgent_alerts.map((a, i) => (
            <p key={i} className="text-xs text-red-300">⚠ {a}</p>
          ))}
        </div>
      )}

      {/* Comparison */}
      {(analysis.comparison.vs_previous_period || analysis.comparison.response_rate) && (
        <div className="bg-[#111118] border border-[#2A2A3E] rounded-xl p-4 space-y-1">
          {analysis.comparison.vs_previous_period && (
            <p className="text-xs text-slate-400">
              <strong className="text-slate-300">vs Previous Period:</strong> {analysis.comparison.vs_previous_period}
            </p>
          )}
          {analysis.comparison.response_rate && (
            <p className="text-xs text-slate-400">
              <strong className="text-slate-300">Response Rate:</strong> {analysis.comparison.response_rate}
            </p>
          )}
        </div>
      )}

      {/* Complaints + Praises */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {analysis.complaints.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <TrendingDown className="w-4 h-4 text-red-400" /> Top Complaints
            </h3>
            {analysis.complaints.map((c, i) => <ComplaintCard key={i} item={c} index={i} />)}
          </div>
        )}
        {analysis.praises.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-green-400" /> What Customers Love
            </h3>
            {analysis.praises.map((p, i) => <PraiseCard key={i} item={p} index={i} />)}
          </div>
        )}
      </div>

      {/* Action plan */}
      {analysis.action_plan.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-indigo-400" /> Action Plan
          </h3>
          {analysis.action_plan.map((a, i) => <ActionCard key={i} item={a} />)}
        </div>
      )}

      {/* Opportunities */}
      {analysis.opportunities.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Lightbulb className="w-4 h-4 text-amber-400" /> Opportunities
          </h3>
          {analysis.opportunities.map((o, i) => (
            <div key={i} className="bg-blue-500/5 border border-blue-500/20 rounded-xl p-3 text-xs text-blue-300">
              💡 {o}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function IntelligencePage() {
  const [period, setPeriod] = useState<"week" | "month">("month");
  const [locationId, setLocationId] = useState<string>("");
  const [locations, setLocations] = useState<Location[]>([]);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [loading, setLoading] = useState(true);
  const [upgradeRequired, setUpgradeRequired] = useState(false);
  const [reviewCount, setReviewCount] = useState<number | null>(null);
  const [downloading, setDownloading] = useState(false);

  const token = typeof window !== "undefined" ? (localStorage.getItem("air_token") || "") : "";
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Load locations
  useEffect(() => {
    locationsApi.list().then(setLocations).catch(() => {});
  }, []);

  // Load preview
  useEffect(() => {
    setLoading(true);
    setAnalysis(null);
    const params = new URLSearchParams({ period });
    if (locationId) params.set("location_id", locationId);

    fetch(`${base}/analytics/report/preview?${params}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (res) => {
        if (res.status === 402) { setUpgradeRequired(true); return; }
        if (!res.ok) throw new Error("Failed");
        const data = await res.json();
        setAnalysis(data.analysis);
        setMeta(data.meta);
        setReviewCount(data.meta?.total_reviews ?? null);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [period, locationId]);

  async function handleDownload(fmt: "pdf" | "json") {
    setDownloading(true);
    try {
      const params = new URLSearchParams({ period, format: fmt });
      if (locationId) params.set("location_id", locationId);
      const res = await fetch(`${base}/analytics/report/download?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const today = new Date().toISOString().split("T")[0];
      a.download = fmt === "pdf" ? `intelligence-report-${period}-${today}.pdf` : `intelligence-report-${period}-${today}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setDownloading(false);
    }
  }

  // ── Upgrade gate ────────────────────────────────────────────────────────────
  if (upgradeRequired) {
    return (
      <div className="max-w-5xl relative">
        {/* Blurred demo behind */}
        <div className="blur-sm pointer-events-none select-none opacity-60 space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[42, "3.8★", "68%", "+12"].map((v, i) => (
              <div key={i} className="bg-[#111118] border border-[#2A2A3E] rounded-xl p-4 text-center">
                <p className="text-2xl font-bold text-white">{v}</p>
              </div>
            ))}
          </div>
          <ReportView analysis={DEMO_ANALYSIS} meta={DEMO_META} />
        </div>
        {/* Upgrade overlay */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="bg-[#111118]/95 border border-[#2A2A3E] rounded-2xl p-8 text-center space-y-4 max-w-sm mx-4 shadow-2xl">
            <div className="w-12 h-12 bg-indigo-600/10 border border-indigo-500/30 rounded-xl flex items-center justify-center mx-auto">
              <Lock className="w-5 h-5 text-indigo-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">📊 Unlock Business Intelligence</h2>
              <p className="text-sm text-slate-400 mt-1">
                Upgrade to Pro or Agency to generate AI-powered intelligence reports with PDF export.
              </p>
            </div>
            <Link
              href="/dashboard/billing"
              className="inline-block px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg transition-colors"
            >
              Upgrade to Pro
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-indigo-400" />
            <h1 className="text-2xl font-semibold text-white tracking-tight">Business Intelligence</h1>
          </div>
          <p className="text-sm text-slate-500 mt-0.5">Understand what your customers really think</p>
        </div>
        {/* Download buttons */}
        {!loading && analysis && (
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => handleDownload("pdf")}
              disabled={downloading}
              className="flex items-center gap-1.5 px-3 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              {downloading ? "Generating…" : "Download PDF"}
            </button>
            <button
              onClick={() => handleDownload("json")}
              disabled={downloading}
              className="flex items-center gap-1.5 px-3 py-2 bg-[#1A1A2E] hover:bg-[#2A2A3E] disabled:opacity-50 text-slate-300 text-sm font-medium rounded-lg border border-[#2A2A3E] transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              Download JSON
            </button>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex bg-[#111118] border border-[#2A2A3E] rounded-lg overflow-hidden">
          {(["week", "month"] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                period === p
                  ? "bg-indigo-600 text-white"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              This {p.charAt(0).toUpperCase() + p.slice(1)}
            </button>
          ))}
        </div>
        {locations.length > 1 && (
          <select
            value={locationId}
            onChange={(e) => setLocationId(e.target.value)}
            className="bg-[#111118] border border-[#2A2A3E] text-slate-300 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-indigo-500"
          >
            <option value="">All Locations</option>
            {locations.map((l) => (
              <option key={l.id} value={l.id}>{l.name}</option>
            ))}
          </select>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <div className="space-y-4">
          {reviewCount !== null ? (
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <div className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
              Analyzing {reviewCount} reviews with AI…
            </div>
          ) : (
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <div className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
              Loading…
            </div>
          )}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} h="h-20" />)}
          </div>
          <SkeletonCard h="h-20" />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-3">{Array.from({ length: 2 }).map((_, i) => <SkeletonCard key={i} h="h-32" />)}</div>
            <div className="space-y-3">{Array.from({ length: 2 }).map((_, i) => <SkeletonCard key={i} h="h-32" />)}</div>
          </div>
        </div>
      )}

      {/* Report */}
      {!loading && analysis && meta && <ReportView analysis={analysis} meta={meta} />}

      {/* Empty state */}
      {!loading && !analysis && !upgradeRequired && (
        <div className="text-center py-16 text-slate-500 text-sm">
          No reviews found for this period.
        </div>
      )}
    </div>
  );
}
