"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { use, useState } from "react";
import { getClient, getClientConversations } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { ClientUpdateReview } from "@/components/ClientUpdateReview";
import { ClientConversations } from "@/components/ClientConversations";
import { ClientFollowupRecorder } from "@/components/ClientFollowupRecorder";

export default function ClientDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [search, setSearch] = useState("");
  const [draftSearch, setDraftSearch] = useState("");

  const clientQuery = useQuery({
    queryKey: ["clients", id],
    queryFn: () => getClient(id),
  });

  const conversationsQuery = useQuery({
    queryKey: ["clients", id, "conversations", search],
    queryFn: () => getClientConversations(id, search),
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

      <ClientFollowupRecorder key={`record-${id}`} clientId={id} clientName={client.full_name} />
      <ClientUpdateReview key={id} clientId={id} />
      <form className="flex flex-wrap items-end gap-2" onSubmit={event => { event.preventDefault(); setSearch(draftSearch.trim()); }}>
        <label className="min-w-0 flex-1 text-sm">Search this client&apos;s conversations
          <input className="mt-1 block min-h-11 w-full rounded-lg border border-line px-3" value={draftSearch} maxLength={100} onChange={event => setDraftSearch(event.target.value)} placeholder="Search titles, summaries or transcripts" />
        </label>
        <button className="min-h-11 rounded-lg bg-accent px-4 text-white" type="submit">Search</button>
        {search && <button className="min-h-11 px-3 underline" type="button" onClick={() => { setSearch(""); setDraftSearch(""); }}>Clear search</button>}
      </form>
      {search && !conversationsQuery.isLoading && !conversationsQuery.isError && <p role="status">{conversationsQuery.data?.length ?? 0} conversations matching “{search}”</p>}
      <ClientConversations searching={Boolean(search)} conversations={conversationsQuery.data ?? []} loading={conversationsQuery.isLoading} error={conversationsQuery.isError} onRetry={() => { void conversationsQuery.refetch(); }} />
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


    </div>
  );
}
