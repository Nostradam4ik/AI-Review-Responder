import Link from "next/link";

const FEATURES = [
  {
    icon: "🤖",
    title: "AI-Powered Responses",
    desc: "Generate professional, on-brand replies to every review in seconds using Groq AI. Choose formal, warm, or casual tone.",
  },
  {
    icon: "🌍",
    title: "Multilingual",
    desc: "Automatically detects the review language and responds in the same language — French, English, Ukrainian, German, Spanish, and more.",
  },
  {
    icon: "⚡",
    title: "Google Business Sync",
    desc: "Connect your Google Business Profile and publish responses directly to Google — without leaving the dashboard.",
  },
  {
    icon: "📊",
    title: "Usage Analytics",
    desc: "Track your response rate, average rating, and monthly usage at a glance.",
  },
  {
    icon: "🔔",
    title: "Telegram Notifications",
    desc: "Get instant alerts when new reviews come in, so you never miss a customer.",
  },
  {
    icon: "🔒",
    title: "Secure & Private",
    desc: "Your Google tokens are stored securely. We never post without your approval.",
  },
];

const PLANS = [
  {
    id: "starter",
    name: "Starter",
    price: 29,
    desc: "For small businesses just getting started.",
    locations: 1,
    responses: 50,
    features: ["1 Google Business location", "50 AI responses/month", "Google Business sync", "Email support"],
  },
  {
    id: "pro",
    name: "Pro",
    price: 59,
    desc: "For growing businesses with more reviews.",
    locations: 3,
    responses: 200,
    popular: true,
    features: ["3 locations", "200 AI responses/month", "Auto-respond scheduler", "Telegram alerts", "Analytics & CSV export"],
  },
  {
    id: "agency",
    name: "Agency",
    price: 149,
    desc: "For agencies managing multiple clients.",
    locations: 10,
    responses: 0,
    features: ["10 locations", "Unlimited AI responses", "White-label ready", "Priority support"],
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950 text-gray-900 dark:text-zinc-100">
      {/* Navbar */}
      <header className="sticky top-0 z-10 bg-white/80 dark:bg-zinc-950/80 backdrop-blur border-b border-gray-100 dark:border-zinc-900 px-6 py-4 flex items-center justify-between max-w-6xl mx-auto">
        <span className="font-bold text-lg">⭐ AI Review Responder</span>
        <div className="flex items-center gap-3">
          <Link href="/login" className="text-sm text-gray-600 dark:text-zinc-400 hover:text-gray-900 dark:hover:text-zinc-100 transition">
            Sign in
          </Link>
          <Link
            href="/register"
            className="text-sm bg-blue-600 hover:bg-blue-700 text-white font-semibold px-4 py-2 rounded-lg transition"
          >
            Start free trial
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-6 pt-20 pb-16 text-center">
        <div className="inline-flex items-center gap-2 bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300 text-xs font-semibold px-3 py-1.5 rounded-full mb-6">
          14-day free trial · No credit card required
        </div>
        <h1 className="text-5xl sm:text-6xl font-extrabold leading-tight tracking-tight text-gray-900 dark:text-zinc-50">
          Reply to every Google review{" "}
          <span className="text-blue-600 dark:text-blue-400">in seconds</span>
        </h1>
        <p className="mt-6 text-xl text-gray-500 dark:text-zinc-400 max-w-2xl mx-auto leading-relaxed">
          AI Review Responder connects to your Google Business Profile and generates personalized, multilingual responses to customer reviews — automatically.
        </p>
        <div className="mt-8 flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            href="/register"
            className="px-8 py-3.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl text-lg transition shadow-lg shadow-blue-200 dark:shadow-blue-950/50"
          >
            Start free — no card needed
          </Link>
          <Link
            href="/login"
            className="px-8 py-3.5 border border-gray-200 dark:border-zinc-700 text-gray-700 dark:text-zinc-300 font-semibold rounded-xl text-lg hover:bg-gray-50 dark:hover:bg-zinc-900 transition"
          >
            Sign in
          </Link>
        </div>
      </section>

      {/* Social proof strip */}
      <div className="bg-gray-50 dark:bg-zinc-900 border-y border-gray-100 dark:border-zinc-800 py-4">
        <p className="text-center text-sm text-gray-500 dark:text-zinc-400">
          Trusted by restaurants, hotels, and local businesses · Responds in 6+ languages · Powered by Groq AI
        </p>
      </div>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-zinc-100">Everything you need to manage reviews</h2>
          <p className="mt-3 text-gray-500 dark:text-zinc-400">Stop spending hours crafting replies. Let AI do it in seconds.</p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="flex flex-col gap-3 p-6 rounded-2xl border border-gray-100 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:shadow-md dark:hover:shadow-zinc-900 transition"
            >
              <span className="text-3xl">{f.icon}</span>
              <h3 className="font-semibold text-gray-900 dark:text-zinc-100">{f.title}</h3>
              <p className="text-sm text-gray-500 dark:text-zinc-400 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="bg-gray-50 dark:bg-zinc-900 border-y border-gray-100 dark:border-zinc-800 py-20">
        <div className="max-w-5xl mx-auto px-6">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-zinc-100">Simple, transparent pricing</h2>
            <p className="mt-3 text-gray-500 dark:text-zinc-400">Start with a 14-day free trial. Upgrade anytime.</p>
          </div>

          <div className="grid sm:grid-cols-3 gap-6">
            {PLANS.map((p) => (
              <div
                key={p.id}
                className={`relative flex flex-col gap-5 rounded-2xl border p-7 bg-white dark:bg-zinc-950 ${
                  p.popular
                    ? "border-blue-500 dark:border-blue-400 shadow-xl shadow-blue-100 dark:shadow-blue-950/30"
                    : "border-gray-200 dark:border-zinc-700"
                }`}
              >
                {p.popular && (
                  <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-blue-600 text-white text-xs font-bold px-4 py-1 rounded-full">
                    Most popular
                  </span>
                )}
                <div>
                  <p className="font-bold text-lg text-gray-900 dark:text-zinc-100">{p.name}</p>
                  <p className="text-xs text-gray-500 dark:text-zinc-400 mt-0.5">{p.desc}</p>
                  <p className="mt-4 text-4xl font-extrabold text-gray-900 dark:text-zinc-50">
                    €{p.price}
                    <span className="text-base font-normal text-gray-500 dark:text-zinc-400">/mo</span>
                  </p>
                </div>

                <ul className="space-y-2 flex-1">
                  {p.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-gray-600 dark:text-zinc-400">
                      <span className="text-green-500 mt-0.5 shrink-0">✓</span> {f}
                    </li>
                  ))}
                </ul>

                <Link
                  href="/register"
                  className={`text-center py-3 rounded-xl font-semibold text-sm transition ${
                    p.popular
                      ? "bg-blue-600 hover:bg-blue-700 text-white shadow-md shadow-blue-200 dark:shadow-blue-950"
                      : "border border-gray-300 dark:border-zinc-600 text-gray-700 dark:text-zinc-300 hover:bg-gray-50 dark:hover:bg-zinc-900"
                  }`}
                >
                  Start free trial
                </Link>
              </div>
            ))}
          </div>

          <p className="text-center mt-8 text-sm text-gray-400 dark:text-zinc-500">
            All plans include a 14-day free trial. Cancel anytime. Prices in EUR + VAT where applicable.
          </p>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-3xl mx-auto px-6 py-20 text-center">
        <h2 className="text-3xl font-bold text-gray-900 dark:text-zinc-100">Ready to save hours every week?</h2>
        <p className="mt-3 text-gray-500 dark:text-zinc-400">
          Join businesses that already use AI Review Responder to keep customers happy.
        </p>
        <Link
          href="/register"
          className="mt-8 inline-block px-10 py-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl text-lg transition shadow-lg shadow-blue-200 dark:shadow-blue-950/50"
        >
          Get started for free →
        </Link>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-100 dark:border-zinc-900 py-8 px-6">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-sm text-gray-400 dark:text-zinc-500">
          <span>⭐ AI Review Responder</span>
          <div className="flex gap-4">
            <Link href="/login" className="hover:text-gray-600 dark:hover:text-zinc-300 transition">Sign in</Link>
            <Link href="/register" className="hover:text-gray-600 dark:hover:text-zinc-300 transition">Register</Link>
            <a href="#pricing" className="hover:text-gray-600 dark:hover:text-zinc-300 transition">Pricing</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
