"use client";

import { useState } from "react";
import type { Review } from "@/types";
import ResponseEditor from "./ResponseEditor";
import { LockedButton } from "./LockedButton";
import { useTranslations } from "next-intl";
import { Sparkles, ChevronDown, ChevronUp } from "lucide-react";

interface ReviewCardProps {
  review: Review;
  onStatusChange?: () => void;
  hasGoogleAccount?: boolean;
  isTrialExpired?: boolean;
}

// Deterministic avatar color based on author name
const AVATAR_COLORS = [
  "from-indigo-500 to-indigo-700",
  "from-blue-500 to-blue-700",
  "from-emerald-500 to-emerald-700",
  "from-rose-500 to-rose-700",
  "from-violet-500 to-violet-700",
  "from-amber-500 to-amber-700",
];
function avatarColor(name: string): string {
  return AVATAR_COLORS[(name.charCodeAt(0) || 0) % AVATAR_COLORS.length];
}

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
  responded: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  ignored: "bg-slate-500/10 text-slate-400 border border-slate-500/20",
};

function StarRating({ rating }: { rating: number }) {
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((star) => (
        <span key={star} className={`text-sm ${star <= rating ? "text-yellow-400" : "text-slate-700"}`}>★</span>
      ))}
    </div>
  );
}

export default function ReviewCard({ review, onStatusChange, hasGoogleAccount = false, isTrialExpired = false }: ReviewCardProps) {
  const [expanded, setExpanded] = useState(false);
  const t = useTranslations("reviews");

  const date = review.review_date
    ? new Date(review.review_date).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })
    : null;

  const initial = review.author_name?.[0]?.toUpperCase() ?? "?";
  const gradientColor = avatarColor(review.author_name ?? "");

  return (
    <div
      className={`bg-[#111118] rounded-xl border border-[#2A2A3E] p-5 space-y-3 transition-all duration-200 hover:border-indigo-500/30 glow-indigo-sm-hover ${
        expanded ? "border-indigo-500/20" : ""
      }`}
      style={expanded ? { boxShadow: "0 0 20px rgba(99,102,241,0.06)" } : undefined}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div
            className={`w-10 h-10 rounded-full bg-gradient-to-br ${gradientColor} flex items-center justify-center text-white font-semibold text-sm shrink-0`}
          >
            {initial}
          </div>
          <div>
            <p className="font-semibold text-white text-sm">{review.author_name ?? "Anonymous"}</p>
            <div className="flex items-center gap-2 mt-1">
              <StarRating rating={review.rating} />
              {date && <span className="text-xs text-slate-500">{date}</span>}
            </div>
          </div>
        </div>
        <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium shrink-0 ${STATUS_BADGE[review.status] ?? STATUS_BADGE.ignored}`}>
          {t(review.status as "pending" | "responded" | "ignored")}
        </span>
      </div>

      {/* Review text */}
      {review.comment && (
        <p className="text-sm text-slate-300 leading-relaxed">{review.comment}</p>
      )}

      {/* Action */}
      {review.status === "pending" && (
        isTrialExpired ? (
          <LockedButton className="text-xs text-indigo-400 font-medium">
            {t("respondWithAI")}
          </LockedButton>
        ) : (
          <button
            onClick={() => setExpanded((v) => !v)}
            className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5" />
            {expanded ? t("hideResponse") : t("respondWithAI")}
            {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        )
      )}

      {/* Response panel */}
      {expanded && (
        <ResponseEditor
          review={review}
          hasGoogleAccount={hasGoogleAccount}
          onPublished={() => {
            setExpanded(false);
            onStatusChange?.();
          }}
        />
      )}
    </div>
  );
}
