"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { locationsApi, usersApi, billingApi } from "@/lib/api";
import { TrialExpiredBanner } from "@/components/TrialExpiredBanner";
import { useSubscription } from "@/hooks/useSubscription";
import type { Location } from "@/types";
import { useTranslations } from "next-intl";
import { RefreshCw, CheckCircle2, MapPin, Save, KeyRound, Bot, ExternalLink, Unlink, Zap, FileText, Lock } from "lucide-react";
import UpgradeModal from "@/components/UpgradeModal";

const BOT_USERNAME = "ReviewAIresponderbot";

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
  const router = useRouter();
  const { isTrialExpired } = useSubscription();

  // Locations
  const [locations, setLocations] = useState<Location[]>([]);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState("");

  // Profile
  const [businessName, setBusinessName] = useState("");
  const [userId, setUserId] = useState("");
  const [tone, setTone] = useState("warm");
  const [language, setLanguage] = useState("auto");
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileMsg, setProfileMsg] = useState("");

  // Telegram
  const [telegramConnected, setTelegramConnected] = useState(false);
  const [telegramDisconnecting, setTelegramDisconnecting] = useState(false);

  // AI Behavior
  const [autoPublish, setAutoPublish] = useState(false);
  const [responseInstructions, setResponseInstructions] = useState("");
  const [aiSaving, setAiSaving] = useState(false);
  const [aiMsg, setAiMsg] = useState("");
  const [canProFeatures, setCanProFeatures] = useState(true);
  const [showUpgradeModal, setShowUpgradeModal] = useState<string | null>(null);

  // Password
  const [hasPassword, setHasPassword] = useState(false);
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [pwSaving, setPwSaving] = useState(false);
  const [pwMsg, setPwMsg] = useState<{ text: string; ok: boolean } | null>(null);

  useEffect(() => {
    locationsApi.list().then(setLocations).catch(console.error);
    usersApi.me().then((u) => {
      setUserId(u.id || "");
      setBusinessName(u.business_name || "");
      setTone(u.tone_preference || "warm");
      setLanguage(u.language || "auto");
      setHasPassword(!!u.has_password);
      setTelegramConnected(!!u.telegram_connected);
      setAutoPublish(!!u.auto_publish);
      setResponseInstructions(u.response_instructions || "");
    }).catch(console.error);
    billingApi.status().then((s) => {
      const isTrial = s.subscription?.status === "trialing";
      const trialActive = isTrial && s.subscription?.trial_end
        ? new Date(s.subscription.trial_end) > new Date()
        : false;
      const hasPro = s.plan?.features?.auto_respond === true;
      setCanProFeatures(trialActive || hasPro);
    }).catch(() => {});
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

  const handleAiSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setAiSaving(true);
    setAiMsg("");
    try {
      await usersApi.update({ auto_publish: autoPublish, response_instructions: responseInstructions });
      setAiMsg("Saved!");
      setTimeout(() => setAiMsg(""), 2000);
    } catch {
      setAiMsg("Failed to save.");
    } finally {
      setAiSaving(false);
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

  const handleTelegramDisconnect = async () => {
    setTelegramDisconnecting(true);
    try {
      await usersApi.telegramDisconnect();
      setTelegramConnected(false);
    } catch {
      // ignore
    } finally {
      setTelegramDisconnecting(false);
    }
  };

  const telegramLink = `https://t.me/${BOT_USERNAME}?start=${userId}`;

  return (
    <div className="space-y-6 max-w-2xl">
      {isTrialExpired && <TrialExpiredBanner />}
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

      {/* AI Responses */}
      <div className={sectionCls}>
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-slate-400" />
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">AI Responses</h2>
        </div>
        <form onSubmit={handleAiSave} className="space-y-5">
          {/* Auto-publish toggle */}
          {isTrialExpired ? (
            <div
              className="flex items-center gap-2 p-4 bg-[#0A0A0F] rounded-lg border border-[#2A2A3E] opacity-50 cursor-not-allowed"
              onClick={() => router.push("/dashboard/billing?reason=trial_expired")}
              title="Upgrade to enable auto-publish"
            >
              <Lock size={14} className="text-slate-400 shrink-0" />
              <span className="text-sm text-slate-500">Auto-publish (upgrade required)</span>
            </div>
          ) : (
            <div
              className={`flex items-start justify-between gap-4 p-4 bg-[#0A0A0F] rounded-lg border border-[#2A2A3E] ${!canProFeatures ? "opacity-60" : ""}`}
            >
              <div className="space-y-1">
                <div className="flex items-center gap-1.5">
                  <p className="text-sm font-medium text-white">Auto-publish responses</p>
                  {!canProFeatures && (
                    <span className="flex items-center gap-1 text-[10px] font-semibold text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-1.5 py-0.5 rounded-full">
                      <Lock className="w-2.5 h-2.5" />
                      Pro
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-500">
                  When enabled, AI responses are published to Google immediately after generation — no manual confirmation needed.
                </p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={autoPublish}
                onClick={() => {
                  if (!canProFeatures) { setShowUpgradeModal("Auto-publish"); return; }
                  setAutoPublish((v) => !v);
                }}
                className={`relative shrink-0 w-10 h-6 rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-[#0A0A0F] ${
                  autoPublish && canProFeatures ? "bg-indigo-600" : "bg-[#2A2A3E]"
                }`}
              >
                <span
                  className={`absolute top-1 left-1 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200 ${
                    autoPublish && canProFeatures ? "translate-x-4" : "translate-x-0"
                  }`}
                />
              </button>
            </div>
          )}

          {/* Response instructions */}
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-slate-400" />
              <label className="text-xs font-medium text-slate-400">Custom response instructions</label>
              {!canProFeatures && (
                <span className="flex items-center gap-1 text-[10px] font-semibold text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-1.5 py-0.5 rounded-full">
                  <Lock className="w-2.5 h-2.5" />
                  Pro
                </span>
              )}
            </div>
            <div className="relative">
              <textarea
                value={responseInstructions}
                onChange={(e) => canProFeatures && setResponseInstructions(e.target.value)}
                onClick={() => { if (!canProFeatures) setShowUpgradeModal("Custom instructions"); }}
                placeholder="e.g. Always mention our loyalty program. Keep responses under 100 words. Sign off with 'The [Business] Team'."
                rows={4}
                readOnly={!canProFeatures}
                className={inputCls + " resize-none" + (!canProFeatures ? " cursor-pointer opacity-60" : "")}
              />
            </div>
            <p className="text-[11px] text-slate-600">
              These instructions are appended to every AI prompt. Leave blank to use defaults.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={aiSaving}
              className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-all disabled:opacity-50 active:scale-95"
            >
              <Save className="w-3.5 h-3.5" />
              {aiSaving ? t("saving") : t("saveChanges")}
            </button>
            {aiMsg && (
              <span className={`text-xs flex items-center gap-1 ${aiMsg === "Saved!" ? "text-emerald-400" : "text-red-400"}`}>
                {aiMsg === "Saved!" && <CheckCircle2 className="w-3.5 h-3.5" />}
                {aiMsg}
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
          <Bot className="w-4 h-4 text-slate-400" />
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">Telegram Notifications</h2>
        </div>

        {telegramConnected ? (
          <div className="flex items-center justify-between gap-4 p-4 bg-emerald-500/5 border border-emerald-500/20 rounded-xl">
            <div className="flex items-center gap-2 text-emerald-400">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <div>
                <p className="text-sm font-semibold">Connected</p>
                <p className="text-xs text-emerald-500/70">You&apos;ll receive review alerts in Telegram</p>
              </div>
            </div>
            <button
              onClick={handleTelegramDisconnect}
              disabled={telegramDisconnecting}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-slate-400 hover:text-red-400 border border-[#2A2A3E] hover:border-red-500/30 rounded-lg transition-all disabled:opacity-50"
            >
              <Unlink className="w-3 h-3" />
              {telegramDisconnecting ? "Disconnecting…" : "Disconnect"}
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-xs text-slate-500">
              Get instant alerts in Telegram when new reviews arrive. No configuration needed — just click and connect.
            </p>
            <a
              href={telegramLink}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-2.5 bg-[#2AABEE] hover:bg-[#229ED9] text-white rounded-lg text-sm font-medium transition-all active:scale-95 w-fit"
            >
              <Bot className="w-3.5 h-3.5" />
              Connect Telegram
              <ExternalLink className="w-3 h-3 opacity-70" />
            </a>
            <p className="text-[11px] text-slate-600">
              Opens @{BOT_USERNAME} — press Start to link your account
            </p>
          </div>
        )}
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
      {showUpgradeModal && (
        <UpgradeModal feature={showUpgradeModal} onClose={() => setShowUpgradeModal(null)} />
      )}
    </div>
  );
}
