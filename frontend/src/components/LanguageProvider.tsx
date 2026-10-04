"use client";
import { createContext, useContext, useEffect, useState } from "react";
import { languages, translate, type Language } from "@/lib/onboarding-translations";
const storageKey = "conversationos-interface-language";
function isLanguage(value: string | null): value is Language {
  return value !== null && Object.prototype.hasOwnProperty.call(languages, value);
}
const LanguageContext = createContext({
  language: "en" as Language,
  setLanguage: (_language: Language) => {},
  t: (text: string, values?: Record<string, string>) => translate("en", text, values),
});
export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, updateLanguage] = useState<Language>("en");
  useEffect(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (isLanguage(saved)) updateLanguage(saved);
    } catch { /* Choice still works without browser storage. */ }
  }, []);
  function setLanguage(value: Language) {
    updateLanguage(value);
    try { localStorage.setItem(storageKey, value); } catch { /* Session-only choice. */ }
  }
  return <LanguageContext.Provider value={{ language, setLanguage, t: (text, values) => translate(language, text, values) }}>{children}</LanguageContext.Provider>;
}
export function useLanguage() { return useContext(LanguageContext); }
export function LanguageSelector() {
  const { language, setLanguage } = useLanguage();
  return <label className="flex flex-wrap items-center gap-2 text-sm">
    <span>Language / Lang</span>
    <select aria-label="Language / Lang" className="max-w-full rounded-lg border border-line bg-surface px-3 py-2 text-ink" value={language} onChange={event => { if (isLanguage(event.target.value)) setLanguage(event.target.value); }}>
      {Object.entries(languages).map(([code, name]) => <option key={code} value={code} lang={code}>{name}</option>)}
    </select>
  </label>;
}
export function LanguageNotice() {
  const { language, t } = useLanguage();
  return <details lang={language} className="my-4 rounded-lg border border-line p-3 text-sm text-ink/70">
    <summary className="cursor-pointer font-medium">{t("About this language option")}</summary>
    <p className="mt-2">{t("The welcome and recording steps are translated. Sign-in screens, other pages, and some service messages may still appear in English. This does not change the language of your recordings or AI results.")}</p>
    <p className="mt-2">{t("Creole transcription is experimental. Speak naturally and check the transcript, especially names, amounts, and deadlines.")}</p>
  </details>;
}
