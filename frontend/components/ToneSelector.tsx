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
    <div className="flex gap-1.5">
      {TONES.map((tone) => (
        <button
          key={tone}
          onClick={() => onChange(tone)}
          disabled={disabled}
          className={`px-3 py-1 rounded-full text-xs font-medium border transition-all duration-150 active:scale-95 ${
            value === tone
              ? "bg-indigo-600 text-white border-indigo-600"
              : "bg-transparent text-slate-400 border-[#2A2A3E] hover:border-indigo-500/50 hover:text-slate-200"
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {t(tone)}
        </button>
      ))}
    </div>
  );
}
