"use client";

interface TrialBannerProps {
  daysRemaining: number;
}

export function TrialBanner({ daysRemaining }: TrialBannerProps) {
  if (daysRemaining <= 0) return null;

  const isUrgent = daysRemaining <= 3;

  return (
    <div
      className={`
        w-full px-4 py-3 flex items-center justify-between gap-4
        text-sm font-medium rounded-lg mb-4
        ${
          isUrgent
            ? "bg-amber-50 border border-amber-200 text-amber-800"
            : "bg-teal-50 border border-teal-200 text-teal-800"
        }
      `}
    >
      <span>
        {isUrgent ? "⚠️" : "🎯"}{" "}
        <strong>
          {daysRemaining === 1
            ? "Last day of your trial"
            : `${daysRemaining} days left in your trial`}
        </strong>
        {" "}— you have full access to all Pro features.
      </span>
      <a
        href="/dashboard/billing"
        className={`
          shrink-0 px-3 py-1.5 rounded-md text-xs font-semibold
          transition-colors whitespace-nowrap
          ${
            isUrgent
              ? "bg-amber-600 text-white hover:bg-amber-700"
              : "bg-teal-600 text-white hover:bg-teal-700"
          }
        `}
      >
        Upgrade now
      </a>
    </div>
  );
}
