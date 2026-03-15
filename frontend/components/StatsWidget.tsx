interface StatsWidgetProps {
  label: string;
  value: string | number;
  highlight?: boolean;
}

export default function StatsWidget({ label, value, highlight }: StatsWidgetProps) {
  return (
    <div className={`rounded-xl border p-5 ${
      highlight
        ? "border-orange-200 bg-orange-50 dark:border-orange-900 dark:bg-orange-950/30"
        : "bg-white dark:bg-zinc-900 border-gray-200 dark:border-zinc-800"
    }`}>
      <p className="text-sm text-gray-500 dark:text-zinc-400">{label}</p>
      <p className={`text-3xl font-bold mt-1 ${highlight ? "text-orange-600 dark:text-orange-400" : "text-gray-900 dark:text-zinc-100"}`}>
        {value}
      </p>
    </div>
  );
}
