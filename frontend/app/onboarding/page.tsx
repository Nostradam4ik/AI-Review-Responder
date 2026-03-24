"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/auth";
import { usersApi } from "@/lib/api";
import { CheckCircle2, ArrowRight, Star, Building2, Bot, Chrome } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const BOT_USERNAME = "ReviewAIresponderbot";

const TONES = [
  { value: "formal", label: "Formal", desc: "Professional & polished" },
  { value: "warm", label: "Warm", desc: "Friendly & personal" },
  { value: "casual", label: "Casual", desc: "Relaxed & approachable" },
];

const STEPS = [
  { id: 1, label: "Your business", icon: Building2 },
  { id: 2, label: "Google Business", icon: Chrome },
  { id: 3, label: "Telegram", icon: Bot },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [userId, setUserId] = useState("");

  // Step 1
  const [businessName, setBusinessName] = useState("");
  const [tone, setTone] = useState("warm");
  const [step1Loading, setStep1Loading] = useState(false);
  const [step1Error, setStep1Error] = useState("");

  // Step 3 — Telegram
  const [telegramConnected, setTelegramConnected] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!getToken()) { router.replace("/login"); return; }
    usersApi.me().then((u) => {
      setUserId(u.id);
      if (u.business_name) setBusinessName(u.business_name);
      if (u.tone_preference) setTone(u.tone_preference);
      if (u.telegram_connected) setTelegramConnected(true);
    }).catch(() => {});
  }, [router]);

  // Poll Telegram status while on step 3
  useEffect(() => {
    if (step !== 3 || telegramConnected) return;
    pollRef.current = setInterval(async () => {
      const status = await usersApi.telegramStatus().catch(() => ({ connected: false }));
      if (status.connected) {
        setTelegramConnected(true);
        if (pollRef.current) clearInterval(pollRef.current);
      }
    }, 3000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [step, telegramConnected]);

  async function handleStep1(e: React.FormEvent) {
    e.preventDefault();
    if (!businessName.trim()) { setStep1Error("Please enter your business name"); return; }
    setStep1Error("");
    setStep1Loading(true);
    try {
      await usersApi.update({ business_name: businessName.trim(), tone_preference: tone });
      setStep(2);
    } catch {
      setStep1Error("Failed to save. Please try again.");
    } finally {
      setStep1Loading(false);
    }
  }

  async function finishOnboarding() {
    await usersApi.update({ onboarding_done: true }).catch(() => {});
    router.replace("/dashboard");
  }

  const telegramLink = `https://t.me/${BOT_USERNAME}?start=${userId}`;

  return (
    <div className="min-h-screen bg-[#0A0A0F] flex items-center justify-center p-6">
      <div className="w-full max-w-lg">
        {/* Steps indicator */}
        <div className="flex items-center justify-center gap-0 mb-10">
          {STEPS.map((s, i) => {
            const done = step > s.id;
            const active = step === s.id;
            return (
              <div key={s.id} className="flex items-center">
                <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                  active ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/30"
                  : done ? "text-emerald-400" : "text-slate-600"
                }`}>
                  {done
                    ? <CheckCircle2 className="w-3.5 h-3.5" />
                    : <span className={`w-4 h-4 rounded-full border flex items-center justify-center text-[10px] font-bold ${active ? "border-indigo-500 text-indigo-400" : "border-slate-700 text-slate-700"}`}>{s.id}</span>
                  }
                  <span className={done || active ? "" : "hidden sm:inline"}>{s.label}</span>
                </div>
                {i < STEPS.length - 1 && (
                  <div className={`w-8 h-px mx-1 ${step > s.id ? "bg-emerald-500/40" : "bg-slate-800"}`} />
                )}
              </div>
            );
          })}
        </div>

        <div className="bg-[#111118] rounded-2xl border border-[#2A2A3E] p-8">
          {/* Step 1 — Business info */}
          {step === 1 && (
            <div className="flex flex-col gap-6">
              <div className="text-center">
                <div className="w-12 h-12 bg-indigo-500/10 rounded-xl flex items-center justify-center mx-auto mb-4">
                  <Star className="w-6 h-6 text-indigo-400" fill="currentColor" />
                </div>
                <h1 className="text-2xl font-bold text-white">Welcome! Let&apos;s set up your account</h1>
                <p className="mt-1 text-sm text-slate-400">Your 14-day free trial has started</p>
              </div>

              <form onSubmit={handleStep1} className="flex flex-col gap-5">
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-medium text-slate-400">Business name</label>
                  <input
                    type="text"
                    required
                    value={businessName}
                    onChange={(e) => setBusinessName(e.target.value)}
                    placeholder="Le Petit Bistrot, Smith Plumbing…"
                    className="w-full px-4 py-2.5 rounded-lg border border-[#2A2A3E] bg-[#0A0A0F] text-white placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-indigo-500 text-sm"
                  />
                </div>

                <div className="flex flex-col gap-2">
                  <label className="text-xs font-medium text-slate-400">AI response tone</label>
                  <div className="grid grid-cols-3 gap-2">
                    {TONES.map((t) => (
                      <button
                        key={t.value}
                        type="button"
                        onClick={() => setTone(t.value)}
                        className={`flex flex-col items-center gap-1 px-3 py-3 rounded-xl border text-center transition-all ${
                          tone === t.value
                            ? "border-indigo-500 bg-indigo-500/10 text-indigo-300"
                            : "border-[#2A2A3E] text-slate-400 hover:border-indigo-500/30"
                        }`}
                      >
                        <span className="text-sm font-semibold">{t.label}</span>
                        <span className="text-[10px] opacity-70">{t.desc}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {step1Error && (
                  <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 px-3 py-2 rounded-lg">{step1Error}</p>
                )}

                <button
                  type="submit"
                  disabled={step1Loading}
                  className="flex items-center justify-center gap-2 w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 text-white font-semibold py-3 rounded-xl transition-all active:scale-95"
                >
                  {step1Loading ? "Saving…" : <>Continue <ArrowRight className="w-4 h-4" /></>}
                </button>
              </form>
            </div>
          )}

          {/* Step 2 — Google Business */}
          {step === 2 && (
            <div className="flex flex-col gap-6 text-center">
              <div>
                <div className="w-12 h-12 bg-amber-500/10 rounded-xl flex items-center justify-center mx-auto mb-4">
                  <Chrome className="w-6 h-6 text-amber-400" />
                </div>
                <h2 className="text-2xl font-bold text-white">Connect Google Business</h2>
                <p className="mt-2 text-sm text-slate-400">
                  Connect your Google Business Profile to sync reviews and respond directly from the dashboard.
                </p>
              </div>

              <div className="bg-[#0A0A0F] rounded-xl border border-[#2A2A3E] p-5 text-left space-y-3">
                {[
                  "Sign in with your Google account",
                  "Grant access to your Business Profile",
                  "Reviews sync automatically every 30 min",
                ].map((text, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <span className="w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-400 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">{i + 1}</span>
                    <span className="text-sm text-slate-300">{text}</span>
                  </div>
                ))}
              </div>

              <div className="flex flex-col gap-3">
                <a
                  href={`${API}/auth/login`}
                  className="flex items-center justify-center gap-3 w-full bg-white hover:bg-gray-50 text-gray-700 font-semibold py-3 rounded-xl transition-all active:scale-95 shadow-sm"
                >
                  <svg className="w-4 h-4" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  Connect with Google
                </a>
                <button
                  onClick={() => setStep(3)}
                  className="text-sm text-slate-500 hover:text-slate-300 transition"
                >
                  Skip for now →
                </button>
              </div>
            </div>
          )}

          {/* Step 3 — Telegram */}
          {step === 3 && (
            <div className="flex flex-col gap-6 text-center">
              <div>
                <div className="w-12 h-12 bg-violet-500/10 rounded-xl flex items-center justify-center mx-auto mb-4">
                  <Bot className="w-6 h-6 text-violet-400" />
                </div>
                <h2 className="text-2xl font-bold text-white">Connect Telegram</h2>
                <p className="mt-2 text-sm text-slate-400">
                  Get instant notifications when new reviews come in.
                </p>
              </div>

              {telegramConnected ? (
                <div className="flex flex-col items-center gap-4">
                  <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-5 py-3 rounded-xl">
                    <CheckCircle2 className="w-5 h-5" />
                    <span className="font-semibold">Telegram connected!</span>
                  </div>
                  <button
                    onClick={finishOnboarding}
                    className="flex items-center justify-center gap-2 w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-3 rounded-xl transition-all active:scale-95"
                  >
                    Go to Dashboard <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <div className="flex flex-col gap-4">
                  <div className="bg-[#0A0A0F] rounded-xl border border-[#2A2A3E] p-5 text-left space-y-3">
                    {[
                      "Click the button below to open Telegram",
                      'Press "Start" in the bot chat',
                      "You'll receive a confirmation message",
                    ].map((text, i) => (
                      <div key={i} className="flex items-start gap-3">
                        <span className="w-5 h-5 rounded-full bg-violet-500/20 text-violet-400 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">{i + 1}</span>
                        <span className="text-sm text-slate-300">{text}</span>
                      </div>
                    ))}
                  </div>

                  <a
                    href={telegramLink}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-center gap-2 w-full bg-[#2AABEE] hover:bg-[#229ED9] text-white font-semibold py-3 rounded-xl transition-all active:scale-95"
                  >
                    <Bot className="w-4 h-4" />
                    Open @{BOT_USERNAME}
                  </a>

                  <div className="flex items-center gap-2 text-xs text-slate-500 justify-center">
                    <div className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                    Waiting for connection…
                  </div>

                  <button
                    onClick={finishOnboarding}
                    className="text-sm text-slate-500 hover:text-slate-300 transition"
                  >
                    Skip for now →
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
