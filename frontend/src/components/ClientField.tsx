"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { getClient, linkConversationToClient, unlinkConversationFromClient } from "@/lib/api";

export function ClientField({
  conversationId,
  clientId,
}: {
  conversationId: string;
  clientId: string | null;
}) {
  const queryClient = useQueryClient();
  const [linkInput, setLinkInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const clientQuery = useQuery({
    queryKey: ["clients", clientId],
    queryFn: () => getClient(clientId as string),
    enabled: clientId !== null,
  });

  async function refresh() {
    await queryClient.invalidateQueries({ queryKey: ["conversations", conversationId] });
  }

  async function handleUnlink() {
    if (!clientId) return;
    setIsSubmitting(true);
    try {
      await unlinkConversationFromClient(clientId, conversationId);
      await refresh();
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleLink() {
    if (!linkInput.trim()) return;
    setIsSubmitting(true);
    try {
      await linkConversationToClient(linkInput.trim(), conversationId);
      setLinkInput("");
      await refresh();
    } finally {
      setIsSubmitting(false);
    }
  }

  if (clientId) {
    return (
      <div className="flex items-center gap-2">
        {clientQuery.data ? (
          <Link href={`/clients/${clientId}`} className="text-sm text-accent hover:underline">
            {clientQuery.data.full_name}
          </Link>
        ) : (
          <span className="text-sm text-ink/50">Loading…</span>
        )}
        <button
          type="button"
          onClick={handleUnlink}
          disabled={isSubmitting}
          className="text-xs text-status-failed hover:underline disabled:opacity-50"
        >
          Unlink
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-ink/40">Unmatched</span>
      <input
        type="text"
        value={linkInput}
        onChange={(e) => setLinkInput(e.target.value)}
        placeholder="Client ID"
        className="w-32 rounded border border-line bg-paper px-2 py-0.5 text-xs text-ink"
      />
      <button
        type="button"
        onClick={handleLink}
        disabled={isSubmitting || !linkInput.trim()}
        className="text-xs text-accent hover:underline disabled:opacity-50"
      >
        Link
      </button>
    </div>
  );
}
