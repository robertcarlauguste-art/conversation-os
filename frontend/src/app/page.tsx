"use client";
import { useLanguage } from "@/components/LanguageProvider";
import { SummaryCards } from "@/components/SummaryCards";
import Link from "next/link";

export default function DashboardPage() {
  const { t, language } = useLanguage();
  return (
    <div className="flex flex-col gap-8">
      <div lang={language}>
        <h1 className="font-display text-3xl text-ink">{t("Dashboard")}</h1>
        <p className="mt-1 text-sm text-ink/60">
          {t("Record a conversation, review your tasks, or pick up where you left off.")}
        </p>
      </div>
      <section lang={language} className="rounded-xl border border-line bg-surface p-6">
        <h2 className="font-display text-xl">{t("Capture your next conversation")}</h2>
        <p className="my-3 text-sm">{t("Choose who it’s about, then record or upload audio. We’ll prepare notes and suggested tasks for you to review. Use fictional details during this pilot.")}</p>
        <Link href="/conversations" className="inline-block rounded-lg bg-accent px-5 py-3 text-white">{t("Record a conversation")}</Link>
      </section>
      <SummaryCards />
    </div>
  );
}
