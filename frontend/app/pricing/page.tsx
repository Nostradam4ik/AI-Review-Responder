import Link from "next/link";
import { CheckCircle2, X, Zap, Rocket, Building2, ArrowRight, Star } from "lucide-react";

const PLANS = [
  {
    id: "starter",
    name: "Starter",
    price: 19,
    desc: "For small businesses just getting started.",
    icon: Zap,
    color: "text-slate-400",
    bg: "bg-[#1A1A2E]",
    features: [
      { text: "1 Google Business location", included: true },
      { text: "100 AI responses/month", included: true },
      { text: "Google Business sync", included: true },
      { text: "Basic analytics", included: true },
      { text: "Telegram alerts", included: true },
      { text: "Email support", included: true },
      { text: "CSV export", included: false },
      { text: "Auto-publish responses", included: false },
      { text: "Custom AI instructions", included: false },
    ],
  },
  {
    id: "pro",
    name: "Pro",
    price: 39,
    desc: "For growing businesses with more reviews.",
    icon: Rocket,
    color: "text-indigo-400",
    bg: "bg-indigo-500/10",
    popular: true,
    features: [
      { text: "3 Google Business locations", included: true },
      { text: "Unlimited AI responses", included: true },
      { text: "Google Business sync", included: true },
      { text: "Full analytics", included: true },
      { text: "Telegram alerts", included: true },
      { text: "Priority support", included: true },
      { text: "CSV export", included: true },
      { text: "Auto-publish responses", included: true },
      { text: "Custom AI instructions", included: true },
    ],
  },
  {
    id: "agency",
    name: "Agency",
    price: 79,
    desc: "For agencies managing multiple clients.",
    icon: Building2,
    color: "text-violet-400",
    bg: "bg-violet-500/10",
    features: [
      { text: "10 Google Business locations", included: true },
      { text: "Unlimited AI responses", included: true },
      { text: "Google Business sync", included: true },
      { text: "Full analytics", included: true },
      { text: "Telegram alerts", included: true },
      { text: "Dedicated support", included: true },
      { text: "CSV export", included: true },
      { text: "Auto-publish responses", included: true },
      { text: "Custom AI instructions", included: true },
    ],
  },
];

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0F] text-slate-100">
      {/* Navbar */}
      <header className="sticky top-0 z-10 bg-[#0A0A0F]/80 backdrop-blur border-b border-[#2A2A3E] px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-7 h-7 bg-indigo-600 rounded-lg flex items-center justify-center">
              <Star className="w-3.5 h-3.5 text-white" fill="currentColor" />
            </div>
            <span className="font-semibold text-white text-sm">AI Review Responder</span>
          </Link>
          <div className="flex items-center gap-3">
            <Link href="/login" className="text-sm text-slate-400 hover:text-white transition-colors">
              Sign in
            </Link>
            <Link
              href="/register"
              className="text-sm bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-4 py-2 rounded-lg transition-all active:scale-95"
            >
              Start free trial
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-6 pt-20 pb-12 text-center">
        <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-medium px-4 py-1.5 rounded-full mb-6">
          14-day free trial — no credit card required
        </div>
        <h1 className="text-4xl sm:text-5xl font-bold text-white tracking-tight mb-4">
          Simple, transparent pricing
        </h1>
        <p className="text-xl text-slate-400 max-w-xl mx-auto">
          Start free for 14 days with all features unlocked. Then choose the plan that fits your business.
        </p>
      </section>

      {/* Plans */}
      <section className="max-w-5xl mx-auto px-6 pb-24">
        <div className="grid sm:grid-cols-3 gap-6">
          {PLANS.map((p) => {
            const PlanIcon = p.icon;
            return (
              <div
                key={p.id}
                className={`relative flex flex-col gap-6 rounded-2xl p-7 transition-all ${
                  p.popular
                    ? "border-2 border-indigo-500 bg-[#111118] shadow-[0_0_40px_rgba(99,102,241,0.15)]"
                    : "border border-[#2A2A3E] bg-[#111118] hover:border-indigo-500/30"
                }`}
              >
                {p.popular && (
                  <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-indigo-600 text-white text-[11px] font-bold px-4 py-1 rounded-full">
                    Most Popular
                  </span>
                )}

                {/* Plan header */}
                <div>
                  <div className="flex items-center gap-2.5 mb-4">
                    <div className={`w-9 h-9 ${p.bg} rounded-lg flex items-center justify-center`}>
                      <PlanIcon className={`w-4.5 h-4.5 ${p.color}`} />
                    </div>
                    <div>
                      <p className="font-bold text-white">{p.name}</p>
                      <p className="text-[11px] text-slate-500">{p.desc}</p>
                    </div>
                  </div>
                  <p className="text-4xl font-extrabold text-white">
                    €{p.price}
                    <span className="text-base font-normal text-slate-500">/mo</span>
                  </p>
                  <p className="text-xs text-slate-600 mt-1">+ VAT where applicable</p>
                </div>

                {/* Feature list */}
                <ul className="space-y-2.5 flex-1">
                  {p.features.map((f) => (
                    <li key={f.text} className={`flex items-start gap-2.5 text-sm ${f.included ? "text-slate-400" : "text-slate-600"}`}>
                      {f.included ? (
                        <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                      ) : (
                        <X className="w-4 h-4 text-slate-700 shrink-0 mt-0.5" />
                      )}
                      {f.text}
                    </li>
                  ))}
                </ul>

                {/* CTA */}
                <Link
                  href="/register"
                  className={`flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-sm transition-all active:scale-95 ${
                    p.popular
                      ? "bg-indigo-600 hover:bg-indigo-500 text-white shadow-[0_0_20px_rgba(99,102,241,0.25)]"
                      : "border border-[#2A2A3E] hover:border-indigo-500/40 text-slate-300 hover:text-white hover:bg-[#1A1A2E]"
                  }`}
                >
                  Start Free Trial
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            );
          })}
        </div>

        <p className="text-center mt-8 text-sm text-slate-600">
          All plans include a 14-day free trial with all features. Cancel anytime.
        </p>

        {/* FAQ strip */}
        <div className="mt-16 grid sm:grid-cols-3 gap-6 text-sm">
          {[
            { q: "Do I need a credit card?", a: "No. Start your 14-day free trial with just an email address." },
            { q: "Can I cancel anytime?", a: "Yes, cancel at any time from your dashboard. No questions asked." },
            { q: "What happens after the trial?", a: "You'll be asked to choose a plan. Your data is never deleted." },
          ].map((item) => (
            <div key={item.q} className="p-5 bg-[#111118] rounded-xl border border-[#2A2A3E]">
              <p className="font-semibold text-white mb-2">{item.q}</p>
              <p className="text-slate-500 text-xs leading-relaxed">{item.a}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[#2A2A3E] py-8 px-6">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-sm text-slate-600">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 bg-indigo-600 rounded-md flex items-center justify-center">
              <Star className="w-2.5 h-2.5 text-white" fill="currentColor" />
            </div>
            <span>AI Review Responder by Nostra</span>
          </div>
          <div className="flex gap-5">
            <Link href="/" className="hover:text-slate-400 transition-colors">Home</Link>
            <Link href="/login" className="hover:text-slate-400 transition-colors">Sign in</Link>
            <Link href="/privacy" className="hover:text-slate-400 transition-colors">Privacy</Link>
            <Link href="/terms" className="hover:text-slate-400 transition-colors">Terms</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
