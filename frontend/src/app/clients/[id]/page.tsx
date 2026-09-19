"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { use } from "react";
import { getClient, getClientConversations } from "@/lib/api";
import { conversationTitle, formatDate } from "@/lib/format";
import { ClientUpdateReview } from "@/components/ClientUpdateReview";
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

      <ClientUpdateReview key={id} clientId={id} />
      <div className="rounded-xl border border-line bg-surface p-6">
        <h3 className="text-xs font-medium uppercase tracking-wide text-ink/50">
          Fact history
        </h3>
        <p className="mt-3 text-sm text-ink/60">Details collected from past conversations may conflict or change. Review the source conversation before treating a detail as current.</p>
        {client.facts.length === 0 ? (
          <p className="mt-3 text-sm text-ink/40">Nothing recorded yet.</p>
        ) : (
          <ul className="mt-3 flex flex-col gap-3 text-sm text-ink">
            {client.facts.map((fact) => (
              <li key={fact.id} className="flex flex-col gap-0.5">
                <span>{fact.fact_text}</span>
                <Link className="text-xs text-accent underline" href={`/conversations/${fact.source_conversation_id}`}>Review source conversation</Link>
                <span className="text-xs text-ink/40">
                  Recorded {formatDate(fact.created_at)}
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
                  {conversationTitle(conversation)}
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
