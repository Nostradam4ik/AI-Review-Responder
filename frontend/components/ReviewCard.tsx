"use client";

import { useState } from "react";
import type { Review } from "@/types";
import ResponseEditor from "./ResponseEditor";

interface ReviewCardProps {
  review: Review;
  onStatusChange?: () => void;
}

function StarRating({ rating }: { rating: number }) {
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((star) => (
        <span key={star} className={star <= rating ? "text-yellow-400" : "text-gray-200 dark:text-zinc-700"}>
          ★
        </span>
      ))}
    </div>
  );
}

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-400",
  responded: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400",
  ignored: "bg-gray-100 text-gray-500 dark:bg-zinc-800 dark:text-zinc-400",
};

export default function ReviewCard({ review, onStatusChange }: ReviewCardProps) {
  const [expanded, setExpanded] = useState(false);

  const date = review.review_date
    ? new Date(review.review_date).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })
    : null;

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800 p-5 space-y-3">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center text-white font-bold text-sm shrink-0">
            {review.author_name?.[0]?.toUpperCase() ?? "?"}
          </div>
          <div>
            <p className="font-medium text-gray-900 dark:text-zinc-100 text-sm">{review.author_name ?? "Anonymous"}</p>
            <div className="flex items-center gap-2 mt-0.5">
              <StarRating rating={review.rating} />
              {date && <span className="text-xs text-gray-400 dark:text-zinc-500">{date}</span>}
            </div>
          </div>
        </div>
        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_BADGE[review.status]}`}>
          {review.status}
        </span>
      </div>

      {/* Comment */}
      {review.comment && (
        <p className="text-sm text-gray-700 dark:text-zinc-300 leading-relaxed">{review.comment}</p>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        {review.status === "pending" && (
          <button
            onClick={() => setExpanded((v) => !v)}
            className="text-xs text-blue-600 dark:text-blue-400 font-medium hover:underline"
          >
            {expanded ? "Hide response" : "Respond with AI"}
          </button>
        )}
      </div>

      {/* Response Editor */}
      {expanded && (
        <ResponseEditor
          review={review}
          onPublished={() => {
            setExpanded(false);
            onStatusChange?.();
          }}
        />
      )}
    </div>
  );
}
