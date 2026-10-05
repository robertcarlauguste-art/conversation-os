"use client";
import { useLanguage } from "@/components/LanguageProvider";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { completeActionItem, reviewClientUpdates, getSavedClientReview } from "@/lib/api";

export function ClientUpdateReview({ clientId }: { clientId: string }) {
  const { t } = useLanguage();
  const queryClient = useQueryClient();
  const [confirmed, setConfirmed] = useState<string[]>([]);
  const saved = useQuery({ queryKey: ["client-review", clientId], queryFn: () => getSavedClientReview(clientId) });
  const review = useMutation({ mutationFn: () => reviewClientUpdates(clientId), onSuccess: data => queryClient.setQueryData(["client-review", clientId], data) });
  const data = saved.data;
  const complete = useMutation({
    mutationFn: completeActionItem,
    onSuccess: (_, id) => {
      setConfirmed(previous => [...previous, id]);
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      void queryClient.invalidateQueries({ queryKey: ["memory"] });
      void queryClient.invalidateQueries({ queryKey: ["client-review", clientId] });
    },
  });
  return <section className="rounded-xl border border-line bg-surface p-6">
    <h2 className="font-display text-xl">{t("Latest client details and task review")}</h2>
    <p className="my-3 text-sm text-ink/70">{t("Generate an AI review of this client's linked transcripts. Check the quoted sources before relying on it. Suggestions do not change your history or close tasks automatically. Generate again after adding a conversation.")}</p>
    <button className="rounded-lg bg-accent px-4 py-2 text-white disabled:opacity-50" disabled={saved.isLoading || review.isPending || complete.isPending} onClick={() => { setConfirmed([]); review.mutate(); }}>{review.isPending ? t("Reviewing conversations…") : t("Review client updates")}</button>
    {saved.isError && <p role="alert">{t("Could not load the saved review. Please refresh and try again.")}</p>}
    {data?.stale && <p role="status" className="mt-3">{t("Linked conversations have changed. Generate a new review to see updated details and suggestions.")}</p>}
    {review.isError && <p role="alert" className="mt-3 text-red-700">{review.error.message}</p>}
    {!saved.isError && !review.isPending && data && !data.stale && <div className="mt-5 space-y-4">
      <p className="text-sm">{t("Reviewed")}{" "}{data.conversation_count}{" "}{t("transcribed conversations. Saved")}{" "}{data.saved_at ? new Date(data.saved_at).toLocaleString() : ""}{t(". AI suggestions still need your review.")}</p>
      <h3 className="font-semibold">{t("Latest details to verify")}</h3>
      {data.details.length === 0 && <p>{t("No supported details identified.")}</p>}
      {data.details.map((item, index) => <div key={index} className="rounded-lg border border-line p-3">
        <p><strong>{item.label}:</strong> {item.value}</p>
        <blockquote className="my-2 text-sm text-ink/70">“{item.quote}”</blockquote>
        <Link className="text-sm text-accent underline" href={`/conversations/${item.source_conversation_id}`}>{t("Review source conversation")}</Link>
      </div>)}
      <h3 className="font-semibold">{t("Possibly completed tasks")}</h3>
      {data.completed_actions.length === 0 && <p>{t("No supported completions identified. Existing tasks remain unchanged.")}</p>}
      {data.completed_actions.map(item => <div key={item.action_id} className="rounded-lg border border-line p-3">
        <p>{data.actions[item.action_id]}</p>
        <blockquote className="my-2 text-sm text-ink/70">“{item.quote}”</blockquote>
        <Link className="text-sm text-accent underline" href={`/conversations/${item.source_conversation_id}`}>{t("Review evidence")}</Link>
        <button className="ml-3 rounded-lg border border-line px-3 py-2 disabled:opacity-50" disabled={complete.isPending || confirmed.includes(item.action_id)} onClick={() => complete.mutate(item.action_id)}>{confirmed.includes(item.action_id) ? t("Confirmed complete") : t("Confirm task is complete")}</button>
      </div>)}
      {complete.isError && <p role="alert" className="text-red-700">{complete.error.message}</p>}
    </div>}
  </section>;
}
