import type { Tone } from "@/types";

interface ToneSelectorProps {
  value: Tone;
  onChange: (tone: Tone) => void;
  disabled?: boolean;
}

const TONES: { value: Tone; label: string; description: string }[] = [
  { value: "formal", label: "Formal", description: "Professional & polished" },
  { value: "warm", label: "Warm", description: "Friendly & welcoming" },
  { value: "casual", label: "Casual", description: "Relaxed & approachable" },
];

export default function ToneSelector({ value, onChange, disabled }: ToneSelectorProps) {
  return (
    <div className="flex gap-2">
      {TONES.map((tone) => (
        <button
          key={tone.value}
          onClick={() => onChange(tone.value)}
          disabled={disabled}
          title={tone.description}
          className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
            value === tone.value
              ? "bg-blue-600 text-white border-blue-600"
              : "bg-white text-gray-600 border-gray-200 hover:border-blue-400 hover:text-blue-600"
          } disabled:opacity-50`}
        >
          {tone.label}
        </button>
      ))}
    </div>
  );
}
