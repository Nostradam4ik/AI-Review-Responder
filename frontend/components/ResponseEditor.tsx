"use client";

import { useState } from "react";
import { responsesApi } from "@/lib/api";
import type { Review, Response, Tone } from "@/types";
import ToneSelector from "./ToneSelector";

interface ResponseEditorProps {
  review: Review;
  initialResponse?: Response | null;
  onPublished?: () => void;
}

export default function ResponseEditor({ review, initialResponse, onPublished }: ResponseEditorProps) {
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
      setError("Failed to generate response.");
    } finally {
      setGenerating(false);
    }
  };

  const handlePublish = async () => {
    if (!response) return;
    setPublishing(true);
    setError("");
    try {
      // Save edits first if text changed
      if (text !== response.ai_draft) {
        await responsesApi.edit(response.id, text);
      }
      await responsesApi.publish(response.id);
      onPublished?.();
    } catch {
      setError("Failed to publish response.");
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div className="space-y-3 pt-3 border-t border-gray-100">
      <div className="flex items-center justify-between">
        <ToneSelector value={tone} onChange={setTone} disabled={generating} />
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="px-3 py-1.5 text-xs font-medium bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 disabled:opacity-50 transition"
        >
          {generating ? "Generating..." : response ? "Regenerate" : "Generate AI Response"}
        </button>
      </div>

      {response && (
        <>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={4}
            className="w-full text-sm border border-gray-200 rounded-lg p-3 resize-none focus:outline-none focus:ring-2 focus:ring-blue-300"
            placeholder="AI generated response..."
          />
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400">
              {text.length} chars · via {response.model_used}
              {response.published_at && " · Published ✓"}
            </span>
            {!response.published_at && (
              <button
                onClick={handlePublish}
                disabled={publishing || !text.trim()}
                className="px-4 py-1.5 text-sm font-medium bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition"
              >
                {publishing ? "Publishing..." : "Publish to Google"}
              </button>
            )}
          </div>
        </>
      )}

      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}
