"use client";
import { LanguageNotice, useLanguage } from "@/components/LanguageProvider";
import { ConversationsTable } from "@/components/ConversationsTable";
import { UploadDropzone } from "@/components/UploadDropzone";

export default function ConversationsPage() {
  const { t, language } = useLanguage();
  return (
    <div className="flex flex-col gap-8">
      <div lang={language}>
        <h1 className="font-display text-3xl text-ink">{t("Conversations")}</h1>
        <p className="mt-1 text-sm text-ink/60">
          {t("Every recording that has entered ConversationOS, newest first.")}
        </p>
      </div>
      <LanguageNotice />
      <UploadDropzone />
      <ConversationsTable />
    </div>
  );
}
