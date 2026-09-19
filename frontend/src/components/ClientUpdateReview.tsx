"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { completeActionItem, reviewClientUpdates } from "@/lib/api";

export function ClientUpdateReview({ clientId }: { clientId: string }) {
  const queryClient = useQueryClient();
  const [confirmed, setConfirmed] = useState<string[]>([]);
  const review = useMutation({ mutationFn: () => reviewClientUpdates(clientId) });
  const complete = useMutation({
    mutationFn: completeActionItem,
    onSuccess: (_, id) => {
      setConfirmed(previous => [...previous, id]);
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      void queryClient.invalidateQueries({ queryKey: ["memory"] });
    },
  });
  return <section className="rounded-xl border border-line bg-surface p-6">
    <h2 className="font-display text-xl">Latest client details and task review</h2>
    <p className="my-3 text-sm text-ink/70">Generate an AI review of this client&apos;s linked transcripts. Check the quoted sources before relying on it. Suggestions do not change your history or close tasks automatically. Generate again after adding a conversation.</p>
    <button className="rounded-lg bg-accent px-4 py-2 text-white disabled:opacity-50" disabled={review.isPending || complete.isPending} onClick={() => { setConfirmed([]); review.mutate(); }}>{review.isPending ? "Reviewing conversations…" : "Review client updates"}</button>
    {review.isError && <p role="alert" className="mt-3 text-red-700">{review.error.message}</p>}
    {!review.isPending && !review.isError && review.data && <div className="mt-5 space-y-4">
      <p className="text-sm">Reviewed {review.data.conversation_count} transcribed conversations. This review is temporary; it is not a saved or verified client profile.</p>
      <h3 className="font-semibold">Latest details to verify</h3>
      {review.data.details.length === 0 && <p>No supported details identified.</p>}
      {review.data.details.map((item, index) => <div key={index} className="rounded-lg border border-line p-3">
        <p><strong>{item.label}:</strong> {item.value}</p>
        <blockquote className="my-2 text-sm text-ink/70">“{item.quote}”</blockquote>
        <Link className="text-sm text-accent underline" href={`/conversations/${item.source_conversation_id}`}>Review source conversation</Link>
      </div>)}
      <h3 className="font-semibold">Possibly completed tasks</h3>
      {review.data.completed_actions.length === 0 && <p>No supported completions identified. Existing tasks remain unchanged.</p>}
      {review.data.completed_actions.map(item => <div key={item.action_id} className="rounded-lg border border-line p-3">
        <p>{review.data.actions[item.action_id]}</p>
        <blockquote className="my-2 text-sm text-ink/70">“{item.quote}”</blockquote>
        <Link className="text-sm text-accent underline" href={`/conversations/${item.source_conversation_id}`}>Review evidence</Link>
        <button className="ml-3 rounded-lg border border-line px-3 py-2 disabled:opacity-50" disabled={complete.isPending || confirmed.includes(item.action_id)} onClick={() => complete.mutate(item.action_id)}>{confirmed.includes(item.action_id) ? "Confirmed complete" : "Confirm task is complete"}</button>
      </div>)}
      {complete.isError && <p role="alert" className="text-red-700">{complete.error.message}</p>}
    </div>}
  </section>;
}
