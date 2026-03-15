"use client";

import type { Tone } from "@/types";
import { useTranslations } from "next-intl";

const TONES: Tone[] = ["formal", "warm", "casual"];

interface ToneSelectorProps {
  value: Tone;
  onChange: (tone: Tone) => void;
  disabled?: boolean;
}

export default function ToneSelector({ value, onChange, disabled }: ToneSelectorProps) {
  const t = useTranslations("reviews");

  return (
    <div className="flex gap-2">
      {TONES.map((tone) => (
        <button
          key={tone}
          onClick={() => onChange(tone)}
          disabled={disabled}
          className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
            value === tone
              ? "bg-blue-600 text-white border-blue-600"
              : "bg-white dark:bg-zinc-800 text-gray-600 dark:text-zinc-400 border-gray-200 dark:border-zinc-700 hover:border-blue-400 hover:text-blue-600"
          } disabled:opacity-50`}
        >
          {t(tone)}
        </button>
      ))}
    </div>
  );
}
