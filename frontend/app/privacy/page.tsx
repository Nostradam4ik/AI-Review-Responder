import Link from "next/link";
import { Star } from "lucide-react";

export default function PrivacyPage() {
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
          <Link href="/register" className="text-sm bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-4 py-2 rounded-lg transition-all">
            Start free trial
          </Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-16 space-y-10">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Privacy Policy</h1>
          <p className="text-sm text-slate-500">Last updated: March 2026</p>
        </div>

        <div className="prose prose-invert max-w-none space-y-8 text-sm text-slate-400 leading-relaxed">

          <section className="space-y-3">
            <h2 className="text-base font-semibold text-white">1. Who We Are</h2>
            <p>
              AI Review Responder is operated by <strong className="text-white">Nostra</strong>, a company providing
              AI-powered review management services for restaurants, hotels, and local businesses.
              For data protection inquiries, contact us at{" "}
              <a href="mailto:contact@yourdomain.com" className="text-indigo-400 hover:underline">
                contact@yourdomain.com
              </a>.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-base font-semibold text-white">2. Data We Collect</h2>
            <ul className="list-disc list-inside space-y-1.5 text-slate-400">
              <li><strong className="text-slate-300">Account data:</strong> email address, business name, password hash (if using email login)</li>
              <li><strong className="text-slate-300">Google data:</strong> Google account ID, OAuth tokens (used to sync Google Business reviews)</li>
              <li><strong className="text-slate-300">Review data:</strong> Google Business reviews fetched via API on your behalf</li>
              <li><strong className="text-slate-300">Notification data:</strong> Telegram chat ID (if you connect Telegram alerts)</li>
              <li><strong className="text-slate-300">Usage data:</strong> number of AI responses generated per billing period</li>
              <li><strong className="text-slate-300">Payment data:</strong> Stripe customer ID (we do not store card details — handled by Stripe)</li>
            </ul>
          </section>

          <section className="space-y-3">
            <h2 className="text-base font-semibold text-white">3. How We Use Your Data</h2>
            <ul className="list-disc list-inside space-y-1.5">
              <li>To provide the service: sync reviews, generate AI responses, publish to Google</li>
              <li>To send notifications (Telegram and/or email) about new reviews</li>
              <li>To manage your subscription and billing via Stripe</li>
              <li>To send transactional emails (email verification, password reset)</li>
            </ul>
            <p className="mt-2 text-indigo-300 font-medium">
              We do not sell, rent, or share your personal data with third parties for marketing purposes.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-base font-semibold text-white">4. AI Processing</h2>
            <p>
              Review content is sent to OpenAI&apos;s API to generate response drafts. Review text may be processed
              outside the EU by OpenAI. We send only the review content — no personally identifiable information
              about you is included in AI prompts. Please review{" "}
              <a href="https://openai.com/policies/privacy-policy" target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:underline">
                OpenAI&apos;s Privacy Policy
              </a>{" "}
              for details on their data handling.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-base font-semibold text-white">5. Data Retention</h2>
            <ul className="list-disc list-inside space-y-1.5">
              <li>Your account data is retained as long as your account is active</li>
              <li>Upon account deletion, all personal data is permanently deleted within 30 days</li>
              <li>Review data fetched from Google belongs to your Google Business account and is deleted with your account</li>
            </ul>
          </section>

          <section className="space-y-3">
            <h2 className="text-base font-semibold text-white">6. Data Security</h2>
            <p>
              All data is stored on servers hosted by <strong className="text-slate-300">Hetzner</strong> in the
              European Union (Germany). Connections are encrypted via HTTPS/TLS. OAuth tokens are stored
              encrypted at rest. We follow industry-standard security practices.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-base font-semibold text-white">7. Your Rights (GDPR)</h2>
            <p>Under the GDPR (EU) 2016/679, you have the following rights:</p>
            <ul className="list-disc list-inside space-y-1.5">
              <li><strong className="text-slate-300">Right of access (Art. 15):</strong> request a copy of your personal data</li>
              <li><strong className="text-slate-300">Right to rectification (Art. 16):</strong> correct inaccurate data</li>
              <li><strong className="text-slate-300">Right to erasure (Art. 17):</strong> request deletion of your account and all associated data</li>
              <li><strong className="text-slate-300">Right to data portability (Art. 20):</strong> receive your data in a structured format</li>
              <li><strong className="text-slate-300">Right to object (Art. 21):</strong> object to processing of your data</li>
            </ul>
            <p>
              To exercise any of these rights, contact us at{" "}
              <a href="mailto:contact@yourdomain.com" className="text-indigo-400 hover:underline">
                contact@yourdomain.com
              </a>.
              We will respond within 30 days.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-base font-semibold text-white">8. Cookies</h2>
            <p>
              We use only essential cookies (authentication token stored in localStorage).
              We do not use tracking or advertising cookies.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-base font-semibold text-white">9. Third-Party Services</h2>
            <ul className="list-disc list-inside space-y-1.5">
              <li><strong className="text-slate-300">Google:</strong> OAuth authentication and Google Business Profile API</li>
              <li><strong className="text-slate-300">Stripe:</strong> payment processing (PCI DSS compliant)</li>
              <li><strong className="text-slate-300">OpenAI:</strong> AI response generation</li>
              <li><strong className="text-slate-300">Resend:</strong> transactional email delivery</li>
              <li><strong className="text-slate-300">Telegram:</strong> optional push notification delivery</li>
              <li><strong className="text-slate-300">Hetzner:</strong> EU-based server hosting</li>
            </ul>
          </section>

          <section className="space-y-3">
            <h2 className="text-base font-semibold text-white">10. Contact & Complaints</h2>
            <p>
              For privacy matters: <a href="mailto:contact@yourdomain.com" className="text-indigo-400 hover:underline">contact@yourdomain.com</a>
            </p>
            <p>
              If you believe we have not handled your data correctly, you have the right to lodge a complaint
              with the French data protection authority:{" "}
              <strong className="text-slate-300">CNIL</strong> — <a href="https://www.cnil.fr" target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:underline">www.cnil.fr</a>
            </p>
            <p className="text-xs text-slate-600 mt-2">A French version of this policy is available upon request.</p>
          </section>
        </div>
      </main>

      <footer className="border-t border-[#2A2A3E] py-8 px-6">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-sm text-slate-600">
          <span>© 2026 Nostra — AI Review Responder</span>
          <div className="flex gap-5">
            <Link href="/" className="hover:text-slate-400 transition-colors">Home</Link>
            <Link href="/terms" className="hover:text-slate-400 transition-colors">Terms</Link>
            <Link href="/pricing" className="hover:text-slate-400 transition-colors">Pricing</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
