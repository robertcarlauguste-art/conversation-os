"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { retryConversation } from "@/lib/api";
import type { ConversationStatus } from "@/lib/types";

export function RetryConversation({ id, status }: { id: string; status: ConversationStatus }) {
  const client = useQueryClient();
  const submitting = useRef(false);
  const retry = useMutation({
    mutationFn: () => retryConversation(id),
    onSuccess: (data) => {
      client.setQueryData(["conversations", id], data);
    },
    onSettled: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey: ["conversations"] }),
        client.invalidateQueries({ queryKey: ["dashboard"] }),
        client.invalidateQueries({ queryKey: ["memory", id] }),
        client.invalidateQueries({ queryKey: ["transcript", id] }),
      ]);
      submitting.current = false;
    },
  });

  return (
    <div>
      {status === "FAILED" && (
        <button
          className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          disabled={retry.isPending}
          onClick={() => {
            if (submitting.current) return;
            submitting.current = true;
            retry.mutate();
          }}
        >
          {retry.isPending ? "Queueing retry…" : "Retry"}
        </button>
      )}
      {retry.isSuccess && (status === "QUEUED" || status === "PROCESSING") && <p role="status">Retry queued. Processing will resume shortly.</p>}
      {retry.isError && <p role="alert">Couldn&apos;t queue the retry. Refresh the conversation before trying again.</p>}
    </div>
  );
}
