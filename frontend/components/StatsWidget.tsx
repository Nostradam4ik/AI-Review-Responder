import type { LucideIcon } from "lucide-react";

interface StatsWidgetProps {
  label: string;
  value: string | number;
  highlight?: boolean;
  icon?: LucideIcon;
  variant?: "indigo" | "amber" | "emerald";
  pulse?: boolean;
}

const VARIANTS = {
  indigo: {
    border: "border-indigo-500/20",
    iconBg: "bg-indigo-500/10",
    iconColor: "text-indigo-400",
    valueColor: "text-white",
  },
  amber: {
    border: "border-amber-500/20",
    iconBg: "bg-amber-500/10",
    iconColor: "text-amber-400",
    valueColor: "text-amber-400",
  },
  emerald: {
    border: "border-emerald-500/20",
    iconBg: "bg-emerald-500/10",
    iconColor: "text-emerald-400",
    valueColor: "text-white",
  },
};

export default function StatsWidget({ label, value, highlight, icon: Icon, variant, pulse }: StatsWidgetProps) {
  const v = variant ?? (highlight ? "amber" : "indigo");
  const style = VARIANTS[v];

  return (
    <div className={`bg-[#111118] rounded-xl border ${style.border} p-5 flex flex-col gap-3 hover:-translate-y-0.5 transition-transform duration-150`}>
      <div className="flex items-center justify-between">
        {Icon ? (
          <div className={`w-9 h-9 rounded-lg ${style.iconBg} flex items-center justify-center`}>
            <Icon className={`w-[18px] h-[18px] ${style.iconColor}`} />
          </div>
        ) : <div />}
        {pulse && typeof value === "number" && value > 0 && (
          <span className="w-2 h-2 bg-amber-400 rounded-full pulse-dot" />
        )}
      </div>
      <div>
        <p className={`text-3xl font-bold ${style.valueColor}`}>{value}</p>
        <p className="text-slate-400 text-sm mt-0.5">{label}</p>
      </div>
    </div>
  );
}
