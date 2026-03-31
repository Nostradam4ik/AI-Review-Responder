import { X, Lock } from "lucide-react";
import Link from "next/link";

interface Props {
  feature: string;
  onClose: () => void;
}

export default function UpgradeModal({ feature, onClose }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-[#111118] border border-[#2A2A3E] rounded-2xl p-6 w-full max-w-sm shadow-xl space-y-4">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-500 hover:text-white transition"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
          <Lock className="w-5 h-5 text-indigo-400" />
        </div>

        <div>
          <h3 className="text-base font-semibold text-white">Pro feature</h3>
          <p className="text-sm text-slate-400 mt-1">
            <span className="text-white font-medium">{feature}</span> is available on Pro and Agency plans.
          </p>
        </div>

        <div className="flex gap-2 pt-1">
          <Link
            href="/dashboard/billing"
            className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg text-center transition active:scale-95"
            onClick={onClose}
          >
            Upgrade to Pro
          </Link>
          <button
            onClick={onClose}
            className="px-4 py-2.5 border border-[#2A2A3E] text-slate-400 hover:text-white text-sm font-medium rounded-lg transition"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
