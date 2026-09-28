"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { use } from "react";
import { getConversation } from "@/lib/api";
import { conversationTitle, formatDate, formatDuration, formatFileSize } from "@/lib/format";
import { StatusBadge } from "@/components/StatusBadge";
import { RetryConversation } from "@/components/RetryConversation";
import { ProcessingDetails } from "@/components/ProcessingDetails";
import { MemoryPanel } from "@/components/MemoryPanel";
import { ConversationTitleEditor } from "@/components/ConversationTitleEditor";
import { ClientField } from "@/components/ClientField";

export default function ConversationDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["conversations", id],
    queryFn: () => getConversation(id),
    // Sprint 2: status can change from PROCESSING to COMPLETED/FAILED
    // shortly after upload — keep it current while that's in flight.
    refetchInterval: (query) =>
      query.state.data?.status === "PROCESSING" ||
      query.state.data?.status === "UPLOADED" ||
      query.state.data?.status === "QUEUED"
        ? 3000
        : false,
  });

  if (isLoading) {
    return <p className="py-10 text-center text-sm text-ink/50">Loading conversation…</p>;
  }

  if (isError || !data) {
    return (
      <div className="py-10 text-center">
        <p className="text-sm text-status-failed">Couldn&apos;t find this conversation.</p>
        <Link href="/conversations" className="mt-2 inline-block text-sm text-accent underline">
          Back to Conversations
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <Link href="/conversations" className="text-xs font-medium text-ink/50 hover:text-ink">
          ← Conversations
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <h1 className="min-w-0 break-words font-display text-3xl text-ink [overflow-wrap:anywhere]">{conversationTitle(data)}</h1>
          <StatusBadge status={data.status} />
        </div>
        <ConversationTitleEditor key={id} id={id} title={data.title} />
      </div>

      <dl className="grid gap-4 rounded-xl border border-line bg-surface p-4 sm:grid-cols-2">
        <Field label="Client" value={<ClientField conversationId={data.id} clientId={data.client_id} />} />
        <Field label="Added" value={formatDate(data.created_at)} />
      </dl>
      <RetryConversation key={data.id} id={data.id} status={data.status} />

      <MemoryPanel
        conversationId={data.id}
        status={data.status}
        processingError={data.processing_error}
      />
      <details className="rounded-xl border border-line bg-surface p-4">
        <summary className="cursor-pointer py-2 text-sm font-semibold">Recording & processing details</summary>
        <dl className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="Filename" value={data.filename} />
          <Field label="File size" value={formatFileSize(data.file_size)} />
          <Field label="Duration" value={formatDuration(data.duration_seconds)} />
          <Field label="Source" value={data.source} />
          <Field label="Processing attempts" value={String(data.processing_attempts)} />
        </dl>
        <div className="mt-4"><ProcessingDetails conversation={data} /></div>
      </details>
    </div>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs font-medium uppercase tracking-wide text-ink/50">{label}</dt>
      <dd className="mt-1 break-words text-sm text-ink [overflow-wrap:anywhere]">{value}</dd>
    </div>
  );
}
