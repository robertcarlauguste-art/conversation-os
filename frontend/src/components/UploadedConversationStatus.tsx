"use client";
import { useLanguage } from "./LanguageProvider";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import Link from "next/link";
import { getConversation } from "@/lib/api";

export function UploadedConversationStatus({ id }: { id: string }) {
  const { t, language } = useLanguage();
  const queryClient = useQueryClient();
  const { data, isError, refetch, isFetching } = useQuery({
    queryKey: ["conversations", id],
    queryFn: () => getConversation(id),
    retry: false,
    refetchInterval: (query) =>
      query.state.status === "error" ||
      query.state.data?.status === "COMPLETED" ||
      query.state.data?.status === "FAILED" ? false : 3000,
  });
  const ready = data?.status === "COMPLETED";
  const failed = data?.status === "FAILED";
  useEffect(() => {
    if (!ready && !failed) return;
    void queryClient.invalidateQueries({
      queryKey: ["conversations"],
      predicate: (query) => !(query.queryKey.length === 2 && query.queryKey[1] === id),
    });
    for (const key of ["clients", "dashboard", "client-review"]) {
      void queryClient.invalidateQueries({ queryKey: [key] });
    }
  }, [ready, failed, id, queryClient]);
  return (
    <section lang={language} className="space-y-3 rounded-xl border border-line bg-surface p-4" aria-label={t("Uploaded recording")}>
      <div role="status" aria-live="polite">
        <p className="font-medium">{isError ? t("Audio uploaded. Status temporarily unavailable.") : ready ? t("Your summary and tasks are ready.") : failed ? t("We couldn’t prepare your notes.") : t("Audio uploaded. Preparing your notes…")}</p>
        <p className="mt-2 text-sm text-ink/70">{isError ? t("Check again, or open the conversation for details.") : ready ? t("Review the summary and check any suggested tasks for mistakes.") : failed ? t("Open the conversation to review the issue and retry processing.") : data?.is_stale ? t("This is taking longer than expected. You can open the conversation to check its progress.") : t("You can leave this page. Find your recording in Conversations when you return.")}</p>
      </div>
      <Link className="inline-block text-accent underline" href={`/conversations/${id}`}>
        {ready && !isError ? t("View summary and tasks") : t("Open your conversation")}
      </Link>
      {isError && <button type="button" disabled={isFetching} onClick={() => void refetch()} className="ml-4 text-accent underline disabled:opacity-50">{t("Check again")}</button>}
    </section>
  );
}
