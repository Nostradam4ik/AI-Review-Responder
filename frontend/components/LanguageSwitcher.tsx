"use client";

import { useLocaleContext, type Locale } from "@/components/LocaleProvider";

const LANGUAGES: { code: Locale; label: string }[] = [
  { code: "en", label: "EN" },
  { code: "fr", label: "FR" },
  { code: "uk", label: "UK" },
  { code: "de", label: "DE" },
  { code: "pl", label: "PL" },
  { code: "es", label: "ES" },
];

export function LanguageSwitcher() {
  const { locale, setLocale } = useLocaleContext();

  return (
    <div className="flex items-center">
      {LANGUAGES.map((lang, i) => (
        <span key={lang.code} className="flex items-center">
          {i > 0 && (
            <span className="text-gray-300 dark:text-zinc-600 text-xs select-none mx-0.5">|</span>
          )}
          <button
            onClick={() => setLocale(lang.code)}
            className={`px-1 py-0.5 text-xs font-medium transition-colors ${
              locale === lang.code
                ? "text-blue-600 dark:text-blue-400 underline underline-offset-2"
                : "text-gray-500 dark:text-zinc-400 hover:text-gray-900 dark:hover:text-zinc-100"
            }`}
          >
            {lang.label}
          </button>
        </span>
      ))}
    </div>
  );
}
