"use client";
import { useLanguage } from "@/components/LanguageProvider";
import Link from "next/link";
import { conversationTitle, formatDate } from "@/lib/format";
import type { ClientConversationItem, ConversationStatus } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";

function heading(item: ClientConversationItem) {
  const title = item.title?.trim();
  if (title && !/^(untitled( conversation)?|conversation)$/i.test(title)) return title;
  const preview = item.summary_preview?.trim();
  if (preview) return preview.length > 90 ? `${preview.slice(0, 90).trimEnd()}…` : preview;
  return conversationTitle({ ...item, title: null });
}

export function ClientConversations({ conversations, loading, error, onRetry, searching = false }: {
  conversations: ClientConversationItem[];
  searching?: boolean;
  loading: boolean;
  error: boolean;
  onRetry: () => void;
}) {
  const { t } = useLanguage();
  return <section className="rounded-xl border border-line bg-surface p-4 sm:p-6" aria-label={t("Client conversations")}>
    <h2 className="font-display text-xl">{t("Conversations")}</h2>
    <p className="mt-1 text-sm text-ink/60">{t("Newest first. Preview the AI summary, then open a conversation for the full notes and tasks.")}</p>
    {loading && <p className="mt-3" role="status">{t("Loading conversations…")}</p>}
    {error && <div className="mt-3" role="alert">{t("Couldn't load conversations.")}{" "}<button className="min-h-11 text-accent underline" onClick={onRetry}>{t("Try again")}</button></div>}
    {!loading && !error && conversations.length === 0 && <p className="mt-3 text-sm text-ink/60">{searching ? t("No matching conversations. Try another word or clear your search.") : t("No linked conversations yet.")}</p>}
    {!error && <ul className="mt-4 space-y-3">
      {conversations.map(item => <li key={item.id}>
        <Link href={`/conversations/${item.id}`} className="block min-w-0 rounded-lg border border-line p-4 transition hover:border-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent">
          <div className="flex flex-col items-start gap-2 sm:flex-row sm:justify-between">
            <h3 className="w-full min-w-0 break-words font-semibold text-ink [overflow-wrap:anywhere] sm:w-auto sm:flex-1">{heading(item)}</h3>
            <StatusBadge status={item.status as ConversationStatus} />
          </div>
          <p className="mt-2 text-xs text-ink/60">{t("Recorded")}{" "}<time dateTime={item.created_at}>{formatDate(item.created_at)}</time></p>
          <p className="mt-3 line-clamp-3 break-words text-sm leading-relaxed text-ink/80 [overflow-wrap:anywhere]">{item.summary_preview?.trim() || (["COMPLETED", "FAILED"].includes(item.status) ? t("No summary available. Open this conversation to view its details.") : t("The summary will appear when processing finishes."))}</p>
          <span className="mt-3 inline-block text-sm font-medium text-accent underline">{t("View conversation →")}</span>
        </Link>
      </li>)}
    </ul>}
  </section>;
}
