interface StatsWidgetProps {
  label: string;
  value: string | number;
  highlight?: boolean;
}

export default function StatsWidget({ label, value, highlight }: StatsWidgetProps) {
  return (
    <div className={`bg-white rounded-xl border p-5 ${highlight ? "border-orange-200 bg-orange-50" : "border-gray-200"}`}>
      <p className="text-sm text-gray-500">{label}</p>
      <p className={`text-3xl font-bold mt-1 ${highlight ? "text-orange-600" : "text-gray-900"}`}>
        {value}
      </p>
    </div>
  );
}
