"use client";

import { useState } from "react";
import { responsesApi } from "@/lib/api";
import type { Review, Response, Tone } from "@/types";
import ToneSelector from "./ToneSelector";
import { useTranslations } from "next-intl";
import { RotateCw, Send, AlertCircle } from "lucide-react";

interface ResponseEditorProps {
  review: Review;
  initialResponse?: Response | null;
  onPublished?: () => void;
  hasGoogleAccount?: boolean;
}

export default function ResponseEditor({ review, initialResponse, onPublished, hasGoogleAccount = false }: ResponseEditorProps) {
  const t = useTranslations("reviews");
  const [response, setResponse] = useState<Response | null>(initialResponse ?? null);
  const [tone, setTone] = useState<Tone>("warm");
  const [text, setText] = useState(initialResponse?.final_text ?? initialResponse?.ai_draft ?? "");
  const [generating, setGenerating] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [error, setError] = useState("");

  const handleGenerate = async () => {
    setGenerating(true);
    setError("");
    try {
      const resp = await responsesApi.generate(review.id, tone);
      setResponse(resp);
      setText(resp.ai_draft);
    } catch {
      setError(t("failedGenerate"));
    } finally {
      setGenerating(false);
    }
  };

  const handlePublish = async () => {
    if (!response) return;
    setPublishing(true);
    setError("");
    try {
      if (text !== response.ai_draft) {
        await responsesApi.edit(response.id, text);
      }
      await responsesApi.publish(response.id);
      onPublished?.();
    } catch {
      setError(t("failedPublish"));
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div className="bg-[#0A0A0F] rounded-lg border border-[#2A2A3E] p-4 mt-1 space-y-3">
      {/* Tone + Generate row */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <ToneSelector value={tone} onChange={setTone} disabled={generating} />
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 border border-[#2A2A3E] hover:border-[#3A3A4E] rounded-full px-3 py-1 transition-all duration-150 disabled:opacity-50 active:scale-95"
        >
          <RotateCw className={`w-3 h-3 ${generating ? "animate-spin" : ""}`} />
          {generating ? t("generating") : response ? t("regenerate") : t("generateAIResponse")}
        </button>
      </div>

      {/* Response text area */}
      {response && (
        <>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={4}
            className="w-full text-sm border border-[#2A2A3E] bg-[#111118] text-slate-200 rounded-lg p-3 resize-none focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 placeholder:text-slate-600 transition-colors"
            placeholder="AI generated response..."
          />
          <div className="flex items-center justify-between gap-3">
            <span className="text-xs text-slate-600">
              {text.length} chars · via {response.model_used}
              {response.published_at && <span className="text-emerald-500 ml-1">· {t("published")}</span>}
            </span>

            {!response.published_at && (
              hasGoogleAccount ? (
                <button
                  onClick={handlePublish}
                  disabled={publishing || !text.trim()}
                  className="flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg disabled:opacity-50 transition-all duration-150 active:scale-95"
                >
                  <Send className="w-3.5 h-3.5" />
                  {publishing ? t("publishing") : t("publishToGoogle")}
                </button>
              ) : (
                <span
                  title={t("noGoogleToPublish")}
                  className="flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium bg-[#1A1A2E] text-slate-500 rounded-lg cursor-not-allowed select-none"
                >
                  <Send className="w-3.5 h-3.5" />
                  {t("publishToGoogle")}
                </span>
              )
            )}
          </div>
        </>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 text-xs text-red-400">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
          {error}
        </div>
      )}
    </div>
  );
}
