"use client";
import { useRouter } from "next/navigation";

export function TrialExpiredBanner() {
  const router = useRouter();
  return (
    <div className="w-full px-4 py-3 flex items-center justify-between gap-4
                    bg-red-50 border border-red-200 text-red-800 text-sm
                    font-medium rounded-lg mb-4">
      <span>
        🔒 <strong>Your free trial has ended.</strong>{" "}
        Your reviews are still visible — upgrade to reply and sync new reviews.
      </span>
      <button
        onClick={() => router.push("/dashboard/billing")}
        className="shrink-0 px-3 py-1.5 rounded-md text-xs font-semibold
                   bg-red-600 text-white hover:bg-red-700 transition-colors
                   whitespace-nowrap"
      >
        Choose a plan →
      </button>
    </div>
  );
}
