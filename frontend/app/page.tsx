import Link from "next/link";
import { CheckCircle2, Bot, Globe, Zap, BarChart3, Bell, Shield, ArrowRight, Star } from "lucide-react";

const FEATURES = [
  {
    icon: Bot,
    title: "AI-Powered Responses",
    desc: "Generate professional, on-brand replies to every review in seconds using Groq AI. Choose formal, warm, or casual tone.",
    color: "text-indigo-400",
    bg: "bg-indigo-500/10",
  },
  {
    icon: Globe,
    title: "Multilingual",
    desc: "Automatically detects the review language and responds in the same language — French, English, Ukrainian, German, Spanish, and more.",
    color: "text-blue-400",
    bg: "bg-blue-500/10",
  },
  {
    icon: Zap,
    title: "Google Business Sync",
    desc: "Connect your Google Business Profile and publish responses directly to Google — without leaving the dashboard.",
    color: "text-amber-400",
    bg: "bg-amber-500/10",
  },
  {
    icon: BarChart3,
    title: "Usage Analytics",
    desc: "Track your response rate, average rating, and monthly usage at a glance.",
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
  },
  {
    icon: Bell,
    title: "Telegram Notifications",
    desc: "Get instant alerts when new reviews come in, so you never miss a customer.",
    color: "text-violet-400",
    bg: "bg-violet-500/10",
  },
  {
    icon: Shield,
    title: "Secure & Private",
    desc: "Your Google tokens are stored securely. We never post without your approval.",
    color: "text-rose-400",
    bg: "bg-rose-500/10",
  },
];

const PLANS = [
  {
    id: "starter",
    name: "Starter",
    price: 19,
    desc: "For small businesses just getting started.",
    features: ["1 Google Business location", "100 AI responses/month", "Google Business sync", "Basic analytics", "Telegram alerts", "Email support"],
  },
  {
    id: "pro",
    name: "Pro",
    price: 39,
    desc: "For growing businesses with more reviews.",
    popular: true,
    features: ["3 locations", "Unlimited AI responses", "CSV export", "Auto-publish", "Custom AI instructions", "Full analytics", "Priority support"],
  },
  {
    id: "agency",
    name: "Agency",
    price: 79,
    desc: "For agencies managing multiple clients.",
    features: ["10 locations", "Unlimited AI responses", "White-label ready", "Dedicated support"],
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0F] text-slate-100">
      {/* Navbar */}
      <header className="sticky top-0 z-10 bg-[#0A0A0F]/80 backdrop-blur border-b border-[#2A2A3E] px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-indigo-600 rounded-lg flex items-center justify-center">
              <Star className="w-3.5 h-3.5 text-white" fill="currentColor" />
            </div>
            <span className="font-semibold text-white text-sm">AI Review Responder</span>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/pricing" className="text-sm text-slate-400 hover:text-white transition-colors">
              Pricing
            </Link>
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
      <section className="bg-grid relative overflow-hidden">
        <div className="max-w-4xl mx-auto px-6 pt-24 pb-20 text-center relative z-10">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-medium px-4 py-1.5 rounded-full mb-8">
            <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full pulse-dot" />
            New — AI-powered review management
          </div>

          <h1 className="text-5xl sm:text-6xl font-bold text-white leading-tight tracking-tight mb-6">
            Répondez à tous vos avis{" "}
            <span className="bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
              Google
            </span>{" "}
            en 1 clic
          </h1>

          <p className="text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed mb-10">
            AI Review Responder connects to your Google Business Profile and generates personalized,
            multilingual responses to customer reviews — automatically.
          </p>

          {/* CTA buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/register"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl text-lg transition-all active:scale-95 shadow-[0_0_40px_rgba(99,102,241,0.3)]"
            >
              Commencer gratuitement
              <ArrowRight className="w-5 h-5" />
            </Link>
            <Link
              href="/login"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 border border-[#2A2A3E] hover:border-indigo-500/40 text-slate-300 hover:text-white font-semibold rounded-xl text-lg transition-all hover:bg-[#1A1A2E]/50"
            >
              Voir la démo
            </Link>
          </div>

          {/* Social proof */}
          <div className="mt-12 flex items-center justify-center gap-3 text-sm text-slate-500">
            <div className="flex -space-x-2">
              {["M", "J", "S", "A", "L"].map((letter, i) => (
                <div
                  key={i}
                  className="w-8 h-8 rounded-full border-2 border-[#0A0A0F] flex items-center justify-center text-white text-xs font-bold"
                  style={{
                    background: `hsl(${[250, 210, 160, 290, 320][i]}, 70%, 50%)`,
                  }}
                >
                  {letter}
                </div>
              ))}
            </div>
            <div className="flex items-center gap-1">
              <span className="text-yellow-400 text-xs">★★★★★</span>
              <span>Trusted by 500+ restaurants in France</span>
            </div>
          </div>
        </div>
      </section>

      {/* Social proof strip */}
      <div className="border-y border-[#2A2A3E] py-4 bg-[#111118]/50">
        <p className="text-center text-sm text-slate-500">
          Responds in 6+ languages · Powered by Groq AI · No credit card required
        </p>
      </div>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-6 py-24">
        <div className="text-center mb-14">
          <h2 className="text-3xl font-bold text-white">Everything you need to manage reviews</h2>
          <p className="mt-3 text-slate-400">Stop spending hours crafting replies. Let AI do it in seconds.</p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {FEATURES.map((f) => {
            const Icon = f.icon;
            return (
              <div
                key={f.title}
                className="flex flex-col gap-4 p-6 bg-[#111118] rounded-xl border border-[#2A2A3E] hover:border-indigo-500/30 hover:-translate-y-0.5 transition-all duration-200"
              >
                <div className={`w-10 h-10 ${f.bg} rounded-lg flex items-center justify-center`}>
                  <Icon className={`w-5 h-5 ${f.color}`} />
                </div>
                <h3 className="font-semibold text-white">{f.title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{f.desc}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="bg-[#111118]/50 border-y border-[#2A2A3E] py-24">
        <div className="max-w-5xl mx-auto px-6">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold text-white">Simple, transparent pricing</h2>
            <p className="mt-3 text-slate-400">Start with a 14-day free trial. Upgrade anytime.</p>
          </div>

          <div className="grid sm:grid-cols-3 gap-6">
            {PLANS.map((p) => (
              <div
                key={p.id}
                className={`relative flex flex-col gap-6 rounded-xl p-7 transition-all ${
                  p.popular
                    ? "border-2 border-indigo-500 bg-[#111118] glow-indigo"
                    : "border border-[#2A2A3E] bg-[#111118] hover:border-indigo-500/30"
                }`}
              >
                {p.popular && (
                  <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-indigo-600 text-white text-[11px] font-bold px-4 py-1 rounded-full">
                    Most popular
                  </span>
                )}
                <div>
                  <p className="font-bold text-lg text-white">{p.name}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{p.desc}</p>
                  <p className="mt-5 text-4xl font-extrabold text-white">
                    €{p.price}
                    <span className="text-base font-normal text-slate-500">/mo</span>
                  </p>
                </div>

                <ul className="space-y-2.5 flex-1">
                  {p.features.map((f) => (
                    <li key={f} className="flex items-start gap-2.5 text-sm text-slate-400">
                      <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                      {f}
                    </li>
                  ))}
                </ul>

                <Link
                  href="/register"
                  className={`text-center py-3 rounded-xl font-semibold text-sm transition-all active:scale-95 ${
                    p.popular
                      ? "bg-indigo-600 hover:bg-indigo-500 text-white shadow-[0_0_20px_rgba(99,102,241,0.2)]"
                      : "border border-[#2A2A3E] hover:border-indigo-500/40 text-slate-300 hover:text-white hover:bg-[#1A1A2E]"
                  }`}
                >
                  Start free trial
                </Link>
              </div>
            ))}
          </div>

          <p className="text-center mt-8 text-sm text-slate-600">
            All plans include a 14-day free trial. Cancel anytime. Prices in EUR + VAT where applicable.
          </p>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-3xl mx-auto px-6 py-24 text-center">
        <h2 className="text-3xl font-bold text-white">Ready to save hours every week?</h2>
        <p className="mt-3 text-slate-400">
          Join businesses that already use AI Review Responder to keep customers happy.
        </p>
        <Link
          href="/register"
          className="mt-10 inline-flex items-center gap-2 px-10 py-4 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl text-lg transition-all active:scale-95 shadow-[0_0_40px_rgba(99,102,241,0.25)]"
        >
          Get started for free
          <ArrowRight className="w-5 h-5" />
        </Link>
      </section>

      {/* Footer */}
      <footer className="border-t border-[#2A2A3E] py-8 px-6">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-sm text-slate-600">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 bg-indigo-600 rounded-md flex items-center justify-center">
              <Star className="w-2.5 h-2.5 text-white" fill="currentColor" />
            </div>
            <span>AI Review Responder</span>
          </div>
          <div className="flex gap-5">
            <Link href="/login" className="hover:text-slate-400 transition-colors">Sign in</Link>
            <Link href="/register" className="hover:text-slate-400 transition-colors">Register</Link>
            <Link href="/pricing" className="hover:text-slate-400 transition-colors">Pricing</Link>
            <Link href="/privacy" className="hover:text-slate-400 transition-colors">Privacy</Link>
            <Link href="/terms" className="hover:text-slate-400 transition-colors">Terms</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
