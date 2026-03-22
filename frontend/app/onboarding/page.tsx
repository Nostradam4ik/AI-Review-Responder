"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function OnboardingPage() {
  const router = useRouter();
  const [businessName, setBusinessName] = useState("");
  const [tone, setTone] = useState("warm");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getToken()) router.replace("/login");
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!businessName.trim()) {
      setError("Please enter your business name");
      return;
    }
    setError("");
    setLoading(true);

    try {
      const res = await fetch(`${API}/users/me`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          business_name: businessName.trim(),
          tone_preference: tone,
          onboarding_done: true,
        }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to save");
      }
      router.replace("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setLoading(false);
    }
  }

  const tones = [
    { value: "formal", label: "Formal", desc: "Professional & polished" },
    { value: "warm", label: "Warm", desc: "Friendly & personal" },
    { value: "casual", label: "Casual", desc: "Relaxed & approachable" },
  ];

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-zinc-950">
      <div className="bg-white dark:bg-zinc-900 rounded-2xl shadow-lg dark:shadow-zinc-900/50 border border-transparent dark:border-zinc-800 p-10 w-full max-w-lg flex flex-col gap-8">
        <div className="text-center">
          <span className="text-4xl">🎉</span>
          <h1 className="mt-3 text-2xl font-bold text-gray-900 dark:text-zinc-100">Welcome! Let&apos;s set up your account</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-zinc-400">This takes 30 seconds</p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-6">
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-semibold text-gray-700 dark:text-zinc-300">
              What&apos;s your business name?
            </label>
            <input
              type="text"
              required
              value={businessName}
              onChange={(e) => setBusinessName(e.target.value)}
              placeholder="Le Petit Bistrot, Smith Plumbing, ..."
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-gray-900 dark:text-zinc-100 placeholder-gray-400 dark:placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            />
          </div>

          <div className="flex flex-col gap-2">
            <label className="text-sm font-semibold text-gray-700 dark:text-zinc-300">
              What tone should AI use when responding?
            </label>
            <div className="grid grid-cols-3 gap-3">
              {tones.map((t) => (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => setTone(t.value)}
                  className={`flex flex-col items-center gap-1 px-3 py-4 rounded-xl border-2 transition text-center ${
                    tone === t.value
                      ? "border-blue-500 bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300"
                      : "border-gray-200 dark:border-zinc-700 text-gray-600 dark:text-zinc-400 hover:border-gray-300 dark:hover:border-zinc-600"
                  }`}
                >
                  <span className="text-sm font-semibold">{t.label}</span>
                  <span className="text-xs opacity-70">{t.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {error && (
            <p className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/30 px-3 py-2 rounded-lg">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white font-semibold py-3 rounded-lg transition text-base"
          >
            {loading ? "Saving..." : "Go to Dashboard →"}
          </button>
        </form>

        <p className="text-center text-xs text-gray-400 dark:text-zinc-500">
          Your 14-day free trial has started. No credit card required.
        </p>
      </div>
    </div>
  );
}
