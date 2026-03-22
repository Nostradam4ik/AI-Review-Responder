"use client";

import { useEffect, useState } from "react";
import { locationsApi, usersApi } from "@/lib/api";
import type { Location } from "@/types";
import { useTranslations } from "next-intl";

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
      <h1 className="text-2xl font-bold text-gray-900 dark:text-zinc-100">{t("title")}</h1>

      {/* Profile */}
      <div className="bg-white dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800 p-6">
        <h2 className="text-base font-semibold text-gray-800 dark:text-zinc-200 mb-4">{t("profile")}</h2>
        <form onSubmit={handleProfileSave} className="space-y-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-gray-700 dark:text-zinc-300">{t("businessName")}</label>
            <input
              type="text"
              value={businessName}
              onChange={(e) => setBusinessName(e.target.value)}
              placeholder="Your business name"
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-gray-900 dark:text-zinc-100 placeholder-gray-400 dark:placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-gray-700 dark:text-zinc-300">{t("aiTone")}</label>
            <div className="flex gap-2">
              {TONES.map((t_) => (
                <button
                  key={t_}
                  type="button"
                  onClick={() => setTone(t_)}
                  className={`px-3 py-1.5 rounded-lg border text-sm font-medium transition ${
                    tone === t_
                      ? "border-blue-500 bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300"
                      : "border-gray-200 dark:border-zinc-700 text-gray-600 dark:text-zinc-400 hover:border-gray-300 dark:hover:border-zinc-600"
                  }`}
                >
                  {tR(t_)}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-gray-700 dark:text-zinc-300">{t("responseLanguage")}</label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-gray-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>{l.label}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={profileSaving}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition"
            >
              {profileSaving ? t("saving") : t("saveChanges")}
            </button>
            {profileMsg && (
              <span className="text-sm text-green-600 dark:text-green-400">{profileMsg}</span>
            )}
          </div>
        </form>
      </div>

      {/* Password */}
      {hasPassword && (
        <div className="bg-white dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800 p-6">
          <h2 className="text-base font-semibold text-gray-800 dark:text-zinc-200 mb-4">{t("changePassword")}</h2>
          <form onSubmit={handlePasswordChange} className="space-y-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-gray-700 dark:text-zinc-300">{t("currentPassword")}</label>
              <input
                type="password"
                required
                value={currentPw}
                onChange={(e) => setCurrentPw(e.target.value)}
                placeholder="••••••••"
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-gray-900 dark:text-zinc-100 placeholder-gray-400 dark:placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-gray-700 dark:text-zinc-300">{t("newPassword")}</label>
              <input
                type="password"
                required
                value={newPw}
                onChange={(e) => setNewPw(e.target.value)}
                placeholder="At least 8 characters"
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-gray-900 dark:text-zinc-100 placeholder-gray-400 dark:placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              />
            </div>
            {pwMsg && (
              <p className={`text-sm px-3 py-2 rounded-lg ${pwMsg.ok ? "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950/30" : "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/30"}`}>
                {pwMsg.text}
              </p>
            )}
            <button
              type="submit"
              disabled={pwSaving}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition"
            >
              {pwSaving ? t("saving") : t("updatePassword")}
            </button>
          </form>
        </div>
      )}

      {/* Locations */}
      <div className="bg-white dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800 p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-800 dark:text-zinc-200">{t("locations")}</h2>
          <button
            onClick={handleSyncLocations}
            disabled={syncing}
            className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {syncing ? t("syncing") : t("syncLocations")}
          </button>
        </div>

        {syncMsg && <p className="text-sm text-green-600 dark:text-green-400">{syncMsg}</p>}

        {locations.length === 0 ? (
          <p className="text-gray-400 dark:text-zinc-500 text-sm">{t("noLocations")}</p>
        ) : (
          <ul className="divide-y divide-gray-100 dark:divide-zinc-800">
            {locations.map((loc) => (
              <li key={loc.id} className="py-3 flex items-start gap-3">
                <span className="text-green-500 mt-0.5">✓</span>
                <div>
                  <p className="text-sm font-medium text-gray-800 dark:text-zinc-200">{loc.name}</p>
                  {loc.address && <p className="text-xs text-gray-400 dark:text-zinc-500">{loc.address}</p>}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
