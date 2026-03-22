"use client";

import { Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

function VerifyContent() {
  const searchParams = useSearchParams();
  // The backend redirects to /login?verified=1 after verifying.
  // This page is shown only if someone navigates here directly without a token.
  const error = searchParams.get("error");

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-zinc-950">
      <div className="bg-white dark:bg-zinc-900 rounded-2xl shadow-lg border border-transparent dark:border-zinc-800 p-10 w-full max-w-md flex flex-col items-center gap-4 text-center">
        {error ? (
          <>
            <span className="text-5xl">❌</span>
            <h2 className="text-xl font-bold text-gray-900 dark:text-zinc-100">Verification failed</h2>
            <p className="text-gray-500 dark:text-zinc-400 text-sm">
              This link is invalid or has expired. Please register again or request a new verification email.
            </p>
          </>
        ) : (
          <>
            <span className="text-5xl">📧</span>
            <h2 className="text-xl font-bold text-gray-900 dark:text-zinc-100">Check your email</h2>
            <p className="text-gray-500 dark:text-zinc-400 text-sm">
              We sent you a verification link. Click it to activate your account, then come back to sign in.
            </p>
          </>
        )}
        <Link href="/login" className="mt-2 text-blue-600 dark:text-blue-400 text-sm font-medium hover:underline">
          Back to sign in
        </Link>
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center" />}>
      <VerifyContent />
    </Suspense>
  );
}
