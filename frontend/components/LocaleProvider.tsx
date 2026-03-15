"use client";

import { createContext, useContext, useState, useEffect, useMemo } from "react";
import { NextIntlClientProvider } from "next-intl";
import type { AbstractIntlMessages } from "next-intl";
import enMessages from "@/messages/en.json";
import frMessages from "@/messages/fr.json";
import ukMessages from "@/messages/uk.json";
import deMessages from "@/messages/de.json";
import plMessages from "@/messages/pl.json";
import esMessages from "@/messages/es.json";

export type Locale = "en" | "fr" | "uk" | "de" | "pl" | "es";

const ALL_MESSAGES: Record<Locale, AbstractIntlMessages> = {
  en: enMessages,
  fr: frMessages,
  uk: ukMessages,
  de: deMessages,
  pl: plMessages,
  es: esMessages,
};

const SUPPORTED: Locale[] = ["en", "fr", "uk", "de", "pl", "es"];

type LocaleCtx = { locale: Locale; setLocale: (l: Locale) => void };

const LocaleContext = createContext<LocaleCtx>({ locale: "en", setLocale: () => {} });

export function useLocaleContext() {
  return useContext(LocaleContext);
}

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");

  useEffect(() => {
    const saved = localStorage.getItem("language") as Locale | null;
    if (saved && SUPPORTED.includes(saved)) setLocaleState(saved);
  }, []);

  const setLocale = (l: Locale) => {
    localStorage.setItem("language", l);
    setLocaleState(l);
  };

  const messages = useMemo(() => ALL_MESSAGES[locale], [locale]);

  return (
    <LocaleContext.Provider value={{ locale, setLocale }}>
      <NextIntlClientProvider locale={locale} messages={messages}>
        {children}
      </NextIntlClientProvider>
    </LocaleContext.Provider>
  );
}
