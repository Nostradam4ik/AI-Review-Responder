"use client";

import { useEffect, useState } from "react";
import { locationsApi, usersApi, reviewsApi } from "@/lib/api";
import type { Location } from "@/types";
import { useTranslations } from "next-intl";
import { RefreshCw, CheckCircle2, MapPin, Save, KeyRound, Send } from "lucide-react";

const TONES = ["formal", "warm", "casual"] as const;
const LANGUAGES = [
  { code: "auto", label: "Auto-detect" },
  { code: "en", label: "English" },
  { code: "fr", label: "Français" },
  { code: "uk", label: "Українська" },
  { code: "de", label: "Deutsch" },
  { code: "pl", label: "Polski" },
  { code: "es", label: "Español" },
];

const inputCls =
  "w-full px-4 py-2.5 rounded-lg border border-[#2A2A3E] bg-[#0A0A0F] text-white placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 text-sm transition-colors";

const sectionCls =
  "bg-[#111118] rounded-xl border border-[#2A2A3E] p-6 space-y-5";

export default function SettingsPage() {
  const t = useTranslations("settings");
  const tR = useTranslations("reviews");

  // Locations
  const [locations, setLocations] = useState<Location[]>([]);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState("");

  // Profile
  const [businessName, setBusinessName] = useState("");
  const [tone, setTone] = useState("warm");
  const [language, setLanguage] = useState("auto");
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileMsg, setProfileMsg] = useState("");

  // Telegram
  const [telegramTesting, setTelegramTesting] = useState(false);
  const [telegramMsg, setTelegramMsg] = useState<{ text: string; ok: boolean } | null>(null);

  // Password
  const [hasPassword, setHasPassword] = useState(false);
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [pwSaving, setPwSaving] = useState(false);
  const [pwMsg, setPwMsg] = useState<{ text: string; ok: boolean } | null>(null);

  useEffect(() => {
    locationsApi.list().then(setLocations).catch(console.error);
    usersApi.me().then((u) => {
      setBusinessName(u.business_name || "");
      setTone(u.tone_preference || "warm");
      setLanguage(u.language || "auto");
      setHasPassword(!!u.password_hash);
    }).catch(console.error);
  }, []);

  const handleSyncLocations = async () => {
    setSyncing(true);
    setSyncMsg("");
    try {
      const result = await locationsApi.sync();
      setSyncMsg(t("syncSuccess", { synced: result.synced, new: result.new }));
      setLocations(await locationsApi.list());
    } catch {
      setSyncMsg(t("syncFailed"));
    } finally {
      setSyncing(false);
    }
  };

  const handleProfileSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileSaving(true);
    setProfileMsg("");
    try {
      await usersApi.update({ business_name: businessName, tone_preference: tone, language });
      setProfileMsg("Saved!");
      setTimeout(() => setProfileMsg(""), 2000);
    } catch {
      setProfileMsg("Failed to save.");
    } finally {
      setProfileSaving(false);
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwSaving(true);
    setPwMsg(null);
    try {
      await usersApi.changePassword(currentPw, newPw);
      setPwMsg({ text: "Password updated!", ok: true });
      setCurrentPw("");
      setNewPw("");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed to update password.";
      setPwMsg({ text: msg, ok: false });
    } finally {
      setPwSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-semibold text-white tracking-tight">{t("title")}</h1>

      {/* Profile */}
      <div className={sectionCls}>
        <h2 className="text-sm font-semibold text-white uppercase tracking-wider">{t("profile")}</h2>
        <form onSubmit={handleProfileSave} className="space-y-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-400">{t("businessName")}</label>
            <input
              type="text"
              value={businessName}
              onChange={(e) => setBusinessName(e.target.value)}
              placeholder="Your business name"
              className={inputCls}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-400">{t("aiTone")}</label>
            <div className="flex gap-2">
              {TONES.map((t_) => (
                <button
                  key={t_}
                  type="button"
                  onClick={() => setTone(t_)}
                  className={`px-4 py-2 rounded-lg border text-sm font-medium transition-all duration-150 active:scale-95 ${
                    tone === t_
                      ? "border-indigo-500 bg-indigo-500/10 text-indigo-300"
                      : "border-[#2A2A3E] text-slate-400 hover:border-indigo-500/40 hover:text-slate-200"
                  }`}
                >
                  {tR(t_)}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-400">{t("responseLanguage")}</label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className={inputCls + " cursor-pointer"}
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code} className="bg-[#111118]">
                  {l.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-3 pt-1">
            <button
              type="submit"
              disabled={profileSaving}
              className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-all disabled:opacity-50 active:scale-95"
            >
              <Save className="w-3.5 h-3.5" />
              {profileSaving ? t("saving") : t("saveChanges")}
            </button>
            {profileMsg && (
              <span className={`text-xs flex items-center gap-1 ${profileMsg === "Saved!" ? "text-emerald-400" : "text-red-400"}`}>
                {profileMsg === "Saved!" && <CheckCircle2 className="w-3.5 h-3.5" />}
                {profileMsg}
              </span>
            )}
          </div>
        </form>
      </div>

      {/* Password */}
      {hasPassword && (
        <div className={sectionCls}>
          <div className="flex items-center gap-2">
            <KeyRound className="w-4 h-4 text-slate-400" />
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider">{t("changePassword")}</h2>
          </div>
          <form onSubmit={handlePasswordChange} className="space-y-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-slate-400">{t("currentPassword")}</label>
              <input
                type="password"
                required
                value={currentPw}
                onChange={(e) => setCurrentPw(e.target.value)}
                placeholder="••••••••"
                className={inputCls}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-slate-400">{t("newPassword")}</label>
              <input
                type="password"
                required
                value={newPw}
                onChange={(e) => setNewPw(e.target.value)}
                placeholder="At least 8 characters"
                className={inputCls}
              />
            </div>
            {pwMsg && (
              <p className={`text-xs px-3 py-2 rounded-lg border ${
                pwMsg.ok
                  ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                  : "text-red-400 bg-red-500/10 border-red-500/20"
              }`}>
                {pwMsg.text}
              </p>
            )}
            <button
              type="submit"
              disabled={pwSaving}
              className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-all disabled:opacity-50 active:scale-95"
            >
              {pwSaving ? t("saving") : t("updatePassword")}
            </button>
          </form>
        </div>
      )}

      {/* Telegram */}
      <div className={sectionCls}>
        <div className="flex items-center gap-2">
          <Send className="w-4 h-4 text-slate-400" />
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">Telegram Notifications</h2>
        </div>
        <p className="text-xs text-slate-500">
          Receive instant alerts when new reviews come in. Configure <code className="text-slate-400">TELEGRAM_BOT_TOKEN</code> and <code className="text-slate-400">TELEGRAM_CHAT_ID</code> in your server environment.
        </p>
        <div className="flex items-center gap-3">
          <button
            onClick={async () => {
              setTelegramTesting(true);
              setTelegramMsg(null);
              try {
                const res = await reviewsApi.testTelegram();
                setTelegramMsg({ text: res.message, ok: res.ok });
              } catch {
                setTelegramMsg({ text: "Failed to send test message.", ok: false });
              } finally {
                setTelegramTesting(false);
              }
            }}
            disabled={telegramTesting}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-all disabled:opacity-50 active:scale-95"
          >
            <Send className="w-3.5 h-3.5" />
            {telegramTesting ? "Sending..." : "Send test message"}
          </button>
          {telegramMsg && (
            <span className={`text-xs flex items-center gap-1 ${telegramMsg.ok ? "text-emerald-400" : "text-red-400"}`}>
              {telegramMsg.ok && <CheckCircle2 className="w-3.5 h-3.5" />}
              {telegramMsg.text}
            </span>
          )}
        </div>
      </div>

      {/* Locations */}
      <div className={sectionCls}>
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-slate-400" />
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider">{t("locations")}</h2>
          </div>
          <button
            onClick={handleSyncLocations}
            disabled={syncing}
            className="flex items-center gap-2 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition-all disabled:opacity-50 active:scale-95"
          >
            <RefreshCw className={`w-3 h-3 ${syncing ? "animate-spin" : ""}`} />
            {syncing ? t("syncing") : t("syncLocations")}
          </button>
        </div>

        {syncMsg && (
          <p className="text-xs text-emerald-400">{syncMsg}</p>
        )}

        {locations.length === 0 ? (
          <p className="text-slate-500 text-sm">{t("noLocations")}</p>
        ) : (
          <ul className="space-y-2">
            {locations.map((loc) => (
              <li key={loc.id} className="flex items-start gap-3 p-3 bg-[#0A0A0F] rounded-lg border border-[#2A2A3E]">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium text-white">{loc.name}</p>
                  {loc.address && <p className="text-xs text-slate-500 mt-0.5">{loc.address}</p>}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
