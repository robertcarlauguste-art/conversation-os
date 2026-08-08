"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { use } from "react";
import { getClient, getClientConversations } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { StatusBadge } from "@/components/StatusBadge";
import type { ConversationStatus } from "@/lib/types";

export default function ClientDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);

  const clientQuery = useQuery({
    queryKey: ["clients", id],
    queryFn: () => getClient(id),
  });

  const conversationsQuery = useQuery({
    queryKey: ["clients", id, "conversations"],
    queryFn: () => getClientConversations(id),
  });

  if (clientQuery.isLoading) {
    return <p className="py-10 text-center text-sm text-ink/50">Loading client…</p>;
  }

  if (clientQuery.isError || !clientQuery.data) {
    return (
      <div className="py-10 text-center">
        <p className="text-sm text-status-failed">Couldn&apos;t find this client.</p>
        <Link href="/clients" className="mt-2 inline-block text-sm text-accent underline">
          Back to Clients
        </Link>
      </div>
    );
  }

  const client = clientQuery.data;

  return (
    <div className="flex flex-col gap-8">
      <div>
        <Link href="/clients" className="text-xs font-medium text-ink/50 hover:text-ink">
          ← Clients
        </Link>
        <h1 className="mt-2 font-display text-3xl text-ink">{client.full_name}</h1>
        <p className="mt-1 text-sm text-ink/60">
          {client.email ?? "No email on file"} · {client.phone ?? "No phone on file"}
        </p>
      </div>

      <div className="rounded-xl border border-line bg-surface p-6">
        <h3 className="text-xs font-medium uppercase tracking-wide text-ink/50">
          Remembered Facts
        </h3>
        {client.facts.length === 0 ? (
          <p className="mt-3 text-sm text-ink/40">Nothing recorded yet.</p>
        ) : (
          <ul className="mt-3 flex flex-col gap-3 text-sm text-ink">
            {client.facts.map((fact) => (
              <li key={fact.id} className="flex flex-col gap-0.5">
                <span>{fact.fact_text}</span>
                <span className="text-xs text-ink/40">
                  Recorded {formatDate(fact.created_at)}
                  {fact.confidence !== null && ` · ${Math.round(fact.confidence * 100)}% confidence`}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="rounded-xl border border-line bg-surface p-6">
        <h3 className="text-xs font-medium uppercase tracking-wide text-ink/50">Conversations</h3>
        {conversationsQuery.isLoading && (
          <p className="mt-3 text-sm text-ink/40">Loading…</p>
        )}
        {conversationsQuery.data && conversationsQuery.data.length === 0 && (
          <p className="mt-3 text-sm text-ink/40">No linked conversations yet.</p>
        )}
        {conversationsQuery.data && conversationsQuery.data.length > 0 && (
          <ul className="mt-3 flex flex-col gap-2">
            {conversationsQuery.data.map((conversation) => (
              <li key={conversation.id} className="flex items-center justify-between text-sm">
                <Link
                  href={`/conversations/${conversation.id}`}
                  className="font-medium text-ink hover:text-accent"
                >
                  {conversation.title ?? conversation.filename}
                </Link>
                <StatusBadge status={conversation.status as ConversationStatus} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
