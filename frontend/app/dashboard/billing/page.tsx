"use client";

import { useEffect, useState } from "react";
import { billingApi, BillingStatus } from "@/lib/api";
import { CheckCircle2, Zap, Building2, Rocket } from "lucide-react";

const PLANS = [
  {
    id: "starter",
    name: "Starter",
    price: 29,
    locations: 1,
    responses: 50,
    icon: Zap,
    features: ["AI response generation", "Google Business sync", "Email support"],
  },
  {
    id: "pro",
    name: "Pro",
    price: 59,
    locations: 3,
    responses: 200,
    icon: Rocket,
    features: ["Everything in Starter", "Auto-respond scheduler", "Telegram notifications", "Analytics", "CSV export"],
    popular: true,
  },
  {
    id: "agency",
    name: "Agency",
    price: 149,
    locations: 10,
    responses: 0,
    icon: Building2,
    features: ["Everything in Pro", "Unlimited AI responses", "White-label", "Priority support"],
  },
];

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  trialing: { label: "Free trial", color: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20" },
  active: { label: "Active", color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" },
  past_due: { label: "Past due", color: "bg-amber-500/10 text-amber-400 border-amber-500/20" },
  cancelled: { label: "Cancelled", color: "bg-slate-500/10 text-slate-400 border-slate-500/20" },
  none: { label: "No subscription", color: "bg-slate-500/10 text-slate-400 border-slate-500/20" },
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
  const badge = STATUS_CONFIG[subStatus] ?? STATUS_CONFIG.none;

  const usagePct =
    usage && usage.responses_limit > 0
      ? Math.min(100, Math.round((usage.responses_this_month / usage.responses_limit) * 100))
      : 0;

  const trialDays = subStatus === "trialing" && sub?.trial_end ? daysUntil(sub.trial_end) : 0;
  const trialPct = subStatus === "trialing" && sub?.trial_end
    ? Math.round(((14 - trialDays) / 14) * 100)
    : 0;

  return (
    <div className="space-y-8 max-w-4xl">
      <h1 className="text-2xl font-semibold text-white tracking-tight">Billing</h1>

      {error && (
        <div className="flex items-center gap-2 text-sm text-red-400 bg-red-500/10 border border-red-500/20 px-4 py-3 rounded-xl">
          {error}
        </div>
      )}

      {/* Current plan card */}
      <div className="bg-gradient-to-br from-indigo-900/20 to-[#111118] border border-indigo-500/20 rounded-xl p-6 space-y-5">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Current subscription</p>
            {loading ? (
              <div className="h-7 w-32 bg-[#1A1A2E] rounded animate-pulse" />
            ) : (
              <p className="text-2xl font-bold text-white">{plan?.name ?? "—"}</p>
            )}
          </div>
          <span className={`text-xs font-semibold px-3 py-1 rounded-full border ${badge.color}`}>
            {badge.label}
          </span>
        </div>

        {!loading && plan && (
          <div className="space-y-4">
            {/* Trial countdown */}
            {subStatus === "trialing" && sub?.trial_end && (
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs text-slate-400">
                  <span>{trialDays} days remaining in free trial</span>
                  <span>{trialPct}% used</span>
                </div>
                <div className="w-full h-1.5 bg-[#1A1A2E] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-indigo-500 rounded-full transition-all"
                    style={{ width: `${trialPct}%` }}
                  />
                </div>
              </div>
            )}

            {subStatus === "active" && sub?.current_period_end && (
              <p className="text-sm text-slate-400">
                Renews {new Date(sub.current_period_end).toLocaleDateString()}
              </p>
            )}

            {/* Usage bar */}
            {usage && (
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs text-slate-400">
                  <span>AI responses this month</span>
                  <span className="font-medium text-white">
                    {usage.responses_this_month} / {usage.responses_limit === 0 ? "∞" : usage.responses_limit}
                  </span>
                </div>
                {usage.responses_limit > 0 && (
                  <div className="w-full h-2 bg-[#1A1A2E] rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        usagePct >= 90 ? "bg-red-500" : usagePct >= 70 ? "bg-amber-500" : "bg-indigo-500"
                      }`}
                      style={{ width: `${usagePct}%` }}
                    />
                  </div>
                )}
              </div>
            )}

            {(subStatus === "active" || subStatus === "past_due") && (
              <button
                onClick={handlePortal}
                disabled={portalLoading}
                className="px-4 py-2 border border-[#2A2A3E] hover:border-indigo-500/50 text-slate-300 hover:text-white rounded-lg text-sm font-medium transition-all disabled:opacity-50 active:scale-95"
              >
                {portalLoading ? "Opening..." : "Manage subscription"}
              </button>
            )}
          </div>
        )}
      </div>

      {/* Plan selection */}
      {(subStatus === "trialing" || subStatus === "none" || subStatus === "cancelled") && (
        <div className="space-y-4">
          <h2 className="text-base font-semibold text-white">
            {subStatus === "trialing" ? "Upgrade your plan" : "Choose a plan"}
          </h2>

          <div className="grid gap-4 sm:grid-cols-3">
            {PLANS.map((p) => {
              const isCurrent = plan?.id === p.id;
              const PlanIcon = p.icon;
              return (
                <div
                  key={p.id}
                  className={`relative flex flex-col gap-5 rounded-xl p-6 transition-all duration-150 ${
                    p.popular
                      ? "border-2 border-indigo-500 bg-[#111118] glow-indigo"
                      : "border border-[#2A2A3E] bg-[#111118] hover:border-indigo-500/30"
                  }`}
                >
                  {p.popular && (
                    <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-indigo-600 text-white text-[11px] font-bold px-3 py-1 rounded-full">
                      Popular
                    </span>
                  )}

                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${p.popular ? "bg-indigo-500/20" : "bg-[#1A1A2E]"}`}>
                          <PlanIcon className={`w-4 h-4 ${p.popular ? "text-indigo-400" : "text-slate-400"}`} />
                        </div>
                        <p className="font-semibold text-white">{p.name}</p>
                      </div>
                      <p className="text-3xl font-bold text-white">
                        €{p.price}
                        <span className="text-sm font-normal text-slate-500">/mo</span>
                      </p>
                    </div>
                  </div>

                  <ul className="space-y-2 flex-1">
                    <li className="text-xs text-slate-400 flex items-center gap-2">
                      <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                      {p.locations} location{p.locations > 1 ? "s" : ""}
                    </li>
                    <li className="text-xs text-slate-400 flex items-center gap-2">
                      <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                      {p.responses === 0 ? "Unlimited" : p.responses} AI responses/mo
                    </li>
                    {p.features.map((f) => (
                      <li key={f} className="text-xs text-slate-400 flex items-start gap-2">
                        <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400 shrink-0 mt-0.5" />
                        {f}
                      </li>
                    ))}
                  </ul>

                  <button
                    disabled={isCurrent || checkoutLoading === p.id}
                    onClick={() => handleCheckout(p.id)}
                    className={`w-full py-2.5 rounded-lg text-sm font-semibold transition-all duration-150 active:scale-95 ${
                      isCurrent
                        ? "bg-[#1A1A2E] text-slate-500 cursor-default"
                        : p.popular
                        ? "bg-indigo-600 hover:bg-indigo-500 text-white"
                        : "border border-[#2A2A3E] hover:border-indigo-500/50 text-slate-300 hover:text-white"
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

      {/* Upgrade CTA for active users */}
      {subStatus === "active" && plan && plan.id !== "agency" && (
        <div className="bg-indigo-500/5 border border-indigo-500/20 rounded-xl p-5 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-white">Want more responses or locations?</p>
            <p className="text-xs text-slate-400 mt-0.5">Upgrade your plan anytime — prorate applied automatically.</p>
          </div>
          <button
            onClick={handlePortal}
            disabled={portalLoading}
            className="shrink-0 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg disabled:opacity-60 transition active:scale-95"
          >
            {portalLoading ? "Opening..." : "Upgrade"}
          </button>
        </div>
      )}
    </div>
  );
}
