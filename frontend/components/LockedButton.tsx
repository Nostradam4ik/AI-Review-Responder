"use client";
import { useRouter } from "next/navigation";
import { Lock } from "lucide-react";

interface LockedButtonProps {
  children: React.ReactNode;
  className?: string;
}

export function LockedButton({ children, className = "" }: LockedButtonProps) {
  const router = useRouter();

  return (
    <button
      onClick={() => router.push("/dashboard/billing?reason=trial_expired")}
      className={`relative opacity-60 cursor-not-allowed flex items-center gap-1.5 ${className}`}
      title="Upgrade to continue"
    >
      <Lock size={13} className="shrink-0" />
      {children}
    </button>
  );
}
