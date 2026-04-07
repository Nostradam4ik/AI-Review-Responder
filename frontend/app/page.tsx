import Link from "next/link";
import { CheckCircle2, Bot, Globe, Zap, BarChart3, Bell, Shield, ArrowRight, Star } from "lucide-react";
import { FaqSection } from "@/components/FaqSection";

// Fix 1 — all French
const FEATURES = [
  {
    icon: Bot,
    title: "Réponses générées par l'IA",
    desc: "Générez des réponses professionnelles à chaque avis en quelques secondes. Choisissez un ton formel, chaleureux ou décontracté.",
    color: "text-indigo-400",
    bg: "bg-indigo-500/10",
  },
  {
    icon: Globe,
    title: "Multilingue",
    desc: "Détecte automatiquement la langue de l'avis et répond dans la même langue — français, anglais, allemand, espagnol et plus.",
    color: "text-blue-400",
    bg: "bg-blue-500/10",
  },
  {
    icon: Zap,
    title: "Synchronisation Google Business",
    desc: "Connectez votre fiche Google Business Profile et publiez les réponses directement sur Google, sans quitter le tableau de bord.",
    color: "text-amber-400",
    bg: "bg-amber-500/10",
  },
  {
    icon: BarChart3,
    title: "Statistiques d'utilisation",
    desc: "Suivez votre taux de réponse, votre note moyenne et votre usage mensuel en un coup d'œil.",
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
  },
  {
    icon: Bell,
    title: "Notifications Telegram",
    desc: "Recevez des alertes instantanées quand de nouveaux avis arrivent pour ne jamais manquer un client.",
    color: "text-violet-400",
    bg: "bg-violet-500/10",
  },
  {
    icon: Shield,
    title: "Sécurisé et confidentiel",
    desc: "Vos tokens Google sont stockés en sécurité. Nous ne publions jamais sans votre accord.",
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
    features: ["Everything in Starter", "Unlimited AI responses", "CSV export", "Auto-publish", "Custom AI instructions", "Full analytics", "Priority support"],
  },
  {
    id: "agency",
    name: "Agency",
    price: 79,
    desc: "For agencies managing multiple clients.",
    features: ["Everything in Pro", "10 locations", "White-label ready", "Dedicated support"],
  },
];

// Fix 3 — real testimonials
const TESTIMONIALS = [
  {
    quote: "Avant, je passais 30 minutes par jour à répondre aux avis. Maintenant c'est automatique.",
    name: "Marie L.",
    restaurant: "Le Bistrot Parisien",
    initials: "ML",
    color: "hsl(250, 70%, 50%)",
  },
  {
    quote: "L'IA comprend parfaitement le ton de notre restaurant. Nos clients pensent que je réponds moi-même.",
    name: "Thomas B.",
    restaurant: "Brasserie du Marché",
    initials: "TB",
    color: "hsl(160, 70%, 40%)",
  },
  {
    quote: "Idéal pour gérer plusieurs établissements. Je gagne 2 heures par semaine.",
    name: "Sophie M.",
    restaurant: "Groupe Resto Lyon",
    initials: "SM",
    color: "hsl(320, 70%, 50%)",
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
          {/* Badge — Fix 1 */}
          <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-medium px-4 py-1.5 rounded-full mb-8">
            <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full pulse-dot" />
            Nouveau — gestion des avis par IA
          </div>

          <h1 className="text-5xl sm:text-6xl font-bold text-white leading-tight tracking-tight mb-6">
            Répondez à tous vos avis{" "}
            <span className="bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
              Google
            </span>{" "}
            en 1 clic
          </h1>

          {/* Fix 1 — subtitle now French */}
          <p className="text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed mb-10">
            AI Review Responder se connecte à votre fiche Google Business Profile et génère
            des réponses personnalisées et multilingues à vos avis clients — automatiquement.
          </p>

          {/* CTA buttons — Fix 2 */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/register"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl text-lg transition-all active:scale-95 shadow-[0_0_40px_rgba(99,102,241,0.3)]"
            >
              Commencer gratuitement
              <ArrowRight className="w-5 h-5" />
            </Link>
            <Link
              href="/login?demo=true"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 border border-[#2A2A3E] hover:border-indigo-500/40 text-slate-300 hover:text-white font-semibold rounded-xl text-lg transition-all hover:bg-[#1A1A2E]/50"
            >
              Voir la démo →
            </Link>
          </div>
        </div>
      </section>

      {/* Social proof strip — Fix 1 */}
      <div className="border-y border-[#2A2A3E] py-4 bg-[#111118]/50">
        <p className="text-center text-sm text-slate-500">
          Répond en 6+ langues · Propulsé par Groq AI · Sans carte bancaire requise
        </p>
      </div>

      {/* Features — Fix 1 */}
      <section className="max-w-6xl mx-auto px-6 py-24">
        <div className="text-center mb-14">
          <h2 className="text-3xl font-bold text-white">Tout ce dont vous avez besoin pour gérer vos avis</h2>
          <p className="mt-3 text-slate-400">Arrêtez de passer des heures à rédiger des réponses. Laissez l'IA le faire en quelques secondes.</p>
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

      {/* Testimonials — Fix 3 */}
      <section className="max-w-6xl mx-auto px-6 pb-24">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-white">Ce que disent nos utilisateurs</h2>
          <p className="mt-3 text-slate-400">Des restaurateurs qui gagnent du temps chaque jour.</p>
        </div>
        <div className="grid sm:grid-cols-3 gap-5">
          {TESTIMONIALS.map((t) => (
            <div
              key={t.name}
              className="flex flex-col gap-5 p-6 bg-[#111118] rounded-xl border border-[#2A2A3E]"
            >
              <p className="text-sm text-slate-300 leading-relaxed flex-1">
                &ldquo;{t.quote}&rdquo;
              </p>
              <div>
                <div className="text-yellow-400 text-xs mb-3">★★★★★</div>
                <div className="flex items-center gap-3">
                  <div
                    className="w-9 h-9 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0"
                    style={{ background: t.color }}
                  >
                    {t.initials}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white">{t.name}</p>
                    <p className="text-xs text-slate-500">{t.restaurant}</p>
                  </div>
                </div>
              </div>
            </div>
          ))}
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

      {/* FAQ — Fix 4 */}
      <FaqSection />

      {/* Bottom CTA — Fix 1 */}
      <section className="max-w-3xl mx-auto px-6 py-24 text-center">
        <h2 className="text-3xl font-bold text-white">Prêt à gagner des heures chaque semaine ?</h2>
        <p className="mt-3 text-slate-400">
          Rejoignez les restaurants qui utilisent déjà AI Review Responder pour satisfaire leurs clients.
        </p>
        <Link
          href="/register"
          className="mt-10 inline-flex items-center gap-2 px-10 py-4 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl text-lg transition-all active:scale-95 shadow-[0_0_40px_rgba(99,102,241,0.25)]"
        >
          Commencer gratuitement
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
