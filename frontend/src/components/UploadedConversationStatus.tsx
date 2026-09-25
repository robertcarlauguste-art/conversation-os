"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { getConversation } from "@/lib/api";

export function UploadedConversationStatus({ id }: { id: string }) {
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
  return (
    <section className="space-y-3 rounded-xl border border-line bg-surface p-4" aria-label="Uploaded recording">
      <div role="status" aria-live="polite">
        <p className="font-medium">{isError ? "Audio uploaded. Status temporarily unavailable." : ready ? "Your summary and tasks are ready." : failed ? "We couldn’t prepare your notes." : "Audio uploaded. Preparing your notes…"}</p>
        <p className="mt-2 text-sm text-ink/70">{isError ? "Check again, or open the conversation for details." : ready ? "Review the summary and check any suggested tasks for mistakes." : failed ? "Open the conversation to review the issue and retry processing." : data?.is_stale ? "This is taking longer than expected. You can open the conversation to check its progress." : "You can leave this page. Find your recording in Conversations when you return."}</p>
      </div>
      <Link className="inline-block text-accent underline" href={`/conversations/${id}`}>
        {ready && !isError ? "View summary and tasks" : "Open your conversation"}
      </Link>
      {isError && <button type="button" disabled={isFetching} onClick={() => void refetch()} className="ml-4 text-accent underline disabled:opacity-50">Check again</button>}
    </section>
  );
}
