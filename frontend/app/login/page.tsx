export default function LoginPage() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-zinc-950">
      <div className="bg-white dark:bg-zinc-900 rounded-2xl shadow-lg dark:shadow-zinc-900/50 border border-transparent dark:border-zinc-800 p-10 w-full max-w-md flex flex-col items-center gap-6">
        <div className="flex flex-col items-center gap-2">
          <span className="text-4xl">⭐</span>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-zinc-100">AI Review Responder</h1>
          <p className="text-gray-500 dark:text-zinc-400 text-sm text-center">
            Respond to your Google Business reviews automatically with AI
          </p>
        </div>

        <a
          href={`${apiUrl}/auth/login`}
          className="w-full flex items-center justify-center gap-3 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-lg px-6 py-3 text-gray-700 dark:text-zinc-200 font-medium shadow-sm hover:shadow-md hover:bg-gray-50 dark:hover:bg-zinc-700 transition"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          Continue with Google
        </a>

        <p className="text-xs text-gray-400 dark:text-zinc-500 text-center">
          By signing in, you grant access to your Google Business Profile to manage review responses.
        </p>
      </div>
    </div>
  );
}
