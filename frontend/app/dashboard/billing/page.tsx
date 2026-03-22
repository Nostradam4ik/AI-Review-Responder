"use client";

import { useEffect, useState } from "react";
import { billingApi, BillingStatus } from "@/lib/api";

const PLANS = [
  {
    id: "starter",
    name: "Starter",
    price: 29,
    locations: 1,
    responses: 50,
    features: ["AI response generation", "Google Business sync", "Email support"],
  },
  {
    id: "pro",
    name: "Pro",
    price: 59,
    locations: 3,
    responses: 200,
    features: ["Everything in Starter", "Auto-respond scheduler", "Telegram notifications", "Analytics", "CSV export"],
    popular: true,
  },
  {
    id: "agency",
    name: "Agency",
    price: 149,
    locations: 10,
    responses: 0,
    features: ["Everything in Pro", "Unlimited AI responses", "White-label", "Priority support"],
  },
];

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  trialing: { label: "Free trial", color: "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/30" },
  active: { label: "Active", color: "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950/30" },
  past_due: { label: "Past due", color: "text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/30" },
  cancelled: { label: "Cancelled", color: "text-gray-500 dark:text-zinc-400 bg-gray-100 dark:bg-zinc-800" },
  none: { label: "No subscription", color: "text-gray-500 dark:text-zinc-400 bg-gray-100 dark:bg-zinc-800" },
};

function daysUntil(dateStr: string): number {
  const diff = new Date(dateStr).getTime() - Date.now();
  return Math.max(0, Math.ceil(diff / 86400000));
}

export default function BillingPage() {
  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
  const [portalLoading, setPortalLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    billingApi.status()
      .then(setStatus)
      .catch(() => setError("Failed to load billing info."))
      .finally(() => setLoading(false));
  }, []);

  const handleCheckout = async (planId: string) => {
    setCheckoutLoading(planId);
    try {
      const { checkout_url } = await billingApi.checkout(planId);
      window.location.href = checkout_url;
    } catch {
      setError("Failed to start checkout. Please try again.");
      setCheckoutLoading(null);
    }
  };

  const handlePortal = async () => {
    setPortalLoading(true);
    try {
      const { portal_url } = await billingApi.portal();
      window.location.href = portal_url;
    } catch {
      setError("Billing portal not available. Please subscribe first.");
      setPortalLoading(false);
    }
  };

  const sub = status?.subscription;
  const plan = status?.plan;
  const usage = status?.usage;
  const subStatus = sub?.status || "none";
  const badge = STATUS_LABELS[subStatus] || STATUS_LABELS.none;

  const usagePct = usage && usage.responses_limit > 0
    ? Math.min(100, Math.round((usage.responses_this_month / usage.responses_limit) * 100))
    : 0;

  return (
    <div className="space-y-6 max-w-3xl">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-zinc-100">Billing</h1>

      {error && (
        <p className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/30 px-4 py-3 rounded-xl">
          {error}
        </p>
      )}

      {/* Current plan */}
      <div className="bg-white dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800 p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-800 dark:text-zinc-200">Current subscription</h2>
          <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${badge.color}`}>
            {badge.label}
          </span>
        </div>

        {loading ? (
          <div className="h-16 animate-pulse bg-gray-100 dark:bg-zinc-800 rounded-lg" />
        ) : plan ? (
          <div className="space-y-3">
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold text-gray-900 dark:text-zinc-100">{plan.name}</span>
              <span className="text-gray-500 dark:text-zinc-400 text-sm">€{plan.price_eur}/month</span>
            </div>

            {/* Trial countdown */}
            {subStatus === "trialing" && sub?.trial_end && (
              <p className="text-sm text-blue-600 dark:text-blue-400">
                {daysUntil(sub.trial_end)} days remaining in free trial
              </p>
            )}

            {/* Renewal date */}
            {subStatus === "active" && sub?.current_period_end && (
              <p className="text-sm text-gray-500 dark:text-zinc-400">
                Renews {new Date(sub.current_period_end).toLocaleDateString()}
              </p>
            )}

            {/* Usage bar */}
            {usage && (
              <div className="space-y-1">
                <div className="flex justify-between text-xs text-gray-500 dark:text-zinc-400">
                  <span>AI responses this month</span>
                  <span>
                    {usage.responses_this_month} / {usage.responses_limit === 0 ? "∞" : usage.responses_limit}
                  </span>
                </div>
                {usage.responses_limit > 0 && (
                  <div className="w-full h-2 bg-gray-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${usagePct >= 90 ? "bg-red-500" : usagePct >= 70 ? "bg-amber-500" : "bg-blue-500"}`}
                      style={{ width: `${usagePct}%` }}
                    />
                  </div>
                )}
              </div>
            )}

            {/* Manage button */}
            {(subStatus === "active" || subStatus === "past_due") && (
              <button
                onClick={handlePortal}
                disabled={portalLoading}
                className="mt-2 px-4 py-2 border border-gray-300 dark:border-zinc-700 rounded-lg text-sm font-medium text-gray-700 dark:text-zinc-300 hover:bg-gray-50 dark:hover:bg-zinc-800 disabled:opacity-50 transition"
              >
                {portalLoading ? "Opening..." : "Manage subscription"}
              </button>
            )}
          </div>
        ) : (
          <p className="text-sm text-gray-500 dark:text-zinc-400">No active subscription.</p>
        )}
      </div>

      {/* Plan selection */}
      {(subStatus === "trialing" || subStatus === "none" || subStatus === "cancelled") && (
        <div className="space-y-3">
          <h2 className="text-base font-semibold text-gray-800 dark:text-zinc-200">
            {subStatus === "trialing" ? "Upgrade your plan" : "Choose a plan"}
          </h2>

          <div className="grid gap-4 sm:grid-cols-3">
            {PLANS.map((p) => {
              const isCurrent = plan?.id === p.id;
              return (
                <div
                  key={p.id}
                  className={`relative flex flex-col gap-4 rounded-xl border p-5 ${
                    p.popular
                      ? "border-blue-500 dark:border-blue-400 shadow-md shadow-blue-100 dark:shadow-blue-950/20"
                      : "border-gray-200 dark:border-zinc-700"
                  } bg-white dark:bg-zinc-900`}
                >
                  {p.popular && (
                    <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-blue-600 text-white text-xs font-bold px-3 py-0.5 rounded-full">
                      Popular
                    </span>
                  )}

                  <div>
                    <p className="font-semibold text-gray-900 dark:text-zinc-100">{p.name}</p>
                    <p className="text-2xl font-bold text-gray-900 dark:text-zinc-100 mt-1">
                      €{p.price}<span className="text-sm font-normal text-gray-500 dark:text-zinc-400">/mo</span>
                    </p>
                  </div>

                  <ul className="space-y-1.5 flex-1">
                    <li className="text-xs text-gray-600 dark:text-zinc-400">
                      {p.locations} location{p.locations > 1 ? "s" : ""}
                    </li>
                    <li className="text-xs text-gray-600 dark:text-zinc-400">
                      {p.responses === 0 ? "Unlimited" : p.responses} AI responses/mo
                    </li>
                    {p.features.map((f) => (
                      <li key={f} className="text-xs text-gray-600 dark:text-zinc-400 flex items-start gap-1.5">
                        <span className="text-green-500 mt-0.5">✓</span> {f}
                      </li>
                    ))}
                  </ul>

                  <button
                    disabled={isCurrent || checkoutLoading === p.id}
                    onClick={() => handleCheckout(p.id)}
                    className={`w-full py-2 rounded-lg text-sm font-semibold transition ${
                      isCurrent
                        ? "bg-gray-100 dark:bg-zinc-800 text-gray-400 dark:text-zinc-500 cursor-default"
                        : p.popular
                        ? "bg-blue-600 hover:bg-blue-700 text-white"
                        : "border border-gray-300 dark:border-zinc-600 text-gray-700 dark:text-zinc-300 hover:bg-gray-50 dark:hover:bg-zinc-800"
                    } disabled:opacity-60`}
                  >
                    {isCurrent
                      ? "Current plan"
                      : checkoutLoading === p.id
                      ? "Redirecting..."
                      : `Subscribe — €${p.price}/mo`}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Upgrade CTA for active users on lower plans */}
      {subStatus === "active" && plan && plan.id !== "agency" && (
        <div className="bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800 rounded-xl p-5 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-blue-900 dark:text-blue-200">Want more responses or locations?</p>
            <p className="text-xs text-blue-700 dark:text-blue-400 mt-0.5">Upgrade your plan anytime — prorate applied automatically.</p>
          </div>
          <button
            onClick={handlePortal}
            disabled={portalLoading}
            className="shrink-0 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg disabled:opacity-60 transition"
          >
            {portalLoading ? "Opening..." : "Upgrade"}
          </button>
        </div>
      )}
    </div>
  );
}
