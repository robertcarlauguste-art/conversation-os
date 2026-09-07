"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { use } from "react";
import { getConversation } from "@/lib/api";
import { formatDate, formatDuration, formatFileSize } from "@/lib/format";
import { StatusBadge } from "@/components/StatusBadge";
import { RetryConversation } from "@/components/RetryConversation";
import { ProcessingDetails } from "@/components/ProcessingDetails";
import { MemoryPanel } from "@/components/MemoryPanel";
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
        <div className="mt-2 flex items-center gap-3">
          <h1 className="font-display text-3xl text-ink">{data.title ?? data.filename}</h1>
          <StatusBadge status={data.status} />
        </div>
      </div>

      <dl className="grid grid-cols-2 gap-x-8 gap-y-4 rounded-xl border border-line bg-surface p-6 sm:grid-cols-3">
        <Field label="Filename" value={data.filename} />
        <Field label="Upload Date" value={formatDate(data.created_at)} />
        <Field label="Status" value={<StatusBadge status={data.status} />} />
        <Field label="File Size" value={formatFileSize(data.file_size)} />
        <Field label="Duration" value={formatDuration(data.duration_seconds)} />
        <Field label="Source" value={data.source} />
        <Field label="Processing Attempts" value={String(data.processing_attempts)} />
        <Field
          label="Client"
          value={<ClientField conversationId={data.id} clientId={data.client_id} />}
        />
      </dl>

      <ProcessingDetails conversation={data} />
      <RetryConversation key={data.id} id={data.id} status={data.status} />

      <MemoryPanel
        conversationId={data.id}
        status={data.status}
        processingError={data.processing_error}
      />
    </div>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-ink/50">{label}</dt>
      <dd className="mt-1 text-sm text-ink">{value}</dd>
    </div>
  );
}
