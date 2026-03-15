"use client";

import { useState } from "react";
import { responsesApi } from "@/lib/api";
import type { Review, Response, Tone } from "@/types";
import ToneSelector from "./ToneSelector";
import { useTranslations } from "next-intl";

interface ResponseEditorProps {
  review: Review;
  initialResponse?: Response | null;
  onPublished?: () => void;
}

export default function ResponseEditor({ review, initialResponse, onPublished }: ResponseEditorProps) {
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
    <div className="space-y-3 pt-3 border-t border-gray-100 dark:border-zinc-800">
      <div className="flex items-center justify-between">
        <ToneSelector value={tone} onChange={setTone} disabled={generating} />
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="px-3 py-1.5 text-xs font-medium bg-blue-50 dark:bg-blue-950/50 text-blue-700 dark:text-blue-400 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/50 disabled:opacity-50 transition"
        >
          {generating ? t("generating") : response ? t("regenerate") : t("generateAIResponse")}
        </button>
      </div>

      {response && (
        <>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={4}
            className="w-full text-sm border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-gray-900 dark:text-zinc-100 rounded-lg p-3 resize-none focus:outline-none focus:ring-2 focus:ring-blue-300 dark:focus:ring-blue-700"
            placeholder="AI generated response..."
          />
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400 dark:text-zinc-500">
              {text.length} chars · via {response.model_used}
              {response.published_at && ` · ${t("published")}`}
            </span>
            {!response.published_at && (
              <button
                onClick={handlePublish}
                disabled={publishing || !text.trim()}
                className="px-4 py-1.5 text-sm font-medium bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition"
              >
                {publishing ? t("publishing") : t("publishToGoogle")}
              </button>
            )}
          </div>
        </>
      )}

      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}
