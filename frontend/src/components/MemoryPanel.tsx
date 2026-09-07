"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { getMemoryByConversation, getTranscriptByConversation } from "@/lib/api";
import type { ConversationStatus } from "@/lib/types";
import { WaveformMark } from "./WaveformMark";

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-6">
      <h3 className="text-xs font-medium uppercase tracking-wide text-ink/50">{title}</h3>
      <div className="mt-3">{children}</div>
    </div>
  );
}

function EmptyNote({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-ink/40">{children}</p>;
}

function BulletList({ items }: { items: string[] }) {
  if (items.length === 0) return <EmptyNote>None identified.</EmptyNote>;
  return (
    <ul className="flex flex-col gap-2 text-sm text-ink">
      {items.map((item, i) => (
        <li key={i} className="flex gap-2">
          <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-ink/30" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export function MemoryPanel({
  conversationId,
  status,
  processingError,
}: {
  conversationId: string;
  status: ConversationStatus;
  processingError?: string | null;
}) {
  const memoryQuery = useQuery({
    queryKey: ["memory", conversationId, status],
    queryFn: () => getMemoryByConversation(conversationId),
    // Sprint 2 processes synchronously on upload, but poll briefly in
    // case the page is opened mid-processing (e.g. a slow real STT call).
    refetchInterval: (query) => (query.state.data ? false : 3000),
  });

  const transcriptQuery = useQuery({
    queryKey: ["transcript", conversationId, status],
    queryFn: () => getTranscriptByConversation(conversationId),
    refetchInterval: (query) => (query.state.data ? false : 3000),
  });

  const [transcriptOpen, setTranscriptOpen] = useState(false);

  if (status === "FAILED") {
    return (
      <div className="rounded-xl border border-status-failed/30 bg-surface p-6 text-center">
        <p className="text-sm font-medium text-status-failed">Processing failed</p>
        <p className="mt-1 text-xs text-ink/50">
          {processingError ??
            "Transcription or extraction didn't complete for this conversation."}
        </p>
      </div>
    );
  }

  if (
    memoryQuery.isLoading ||
    status === "QUEUED" ||
    status === "PROCESSING" ||
    status === "UPLOADED"
  ) {
    return (
      <div className="rounded-xl border border-dashed border-line bg-surface py-12 text-center">
        <WaveformMark className="mx-auto h-6 w-auto animate-pulse text-ink/30" />
        <p className="mt-3 text-sm font-medium text-ink">Processing conversation…</p>
        <p className="mt-1 text-xs text-ink/40">
          Transcribing, then extracting summary and key details.
        </p>
      </div>
    );
  }

  if (memoryQuery.isError) {
    return (
      <div className="rounded-xl border border-status-failed/30 bg-surface p-6 text-center">
        <p className="text-sm text-status-failed">
          Couldn&apos;t load this conversation&apos;s memory. Check that the backend is running.
        </p>
      </div>
    );
  }

  const memory = memoryQuery.data;
  const transcript = transcriptQuery.data;

  if (!memory) {
    return (
      <div className="rounded-xl border border-dashed border-line bg-surface py-12 text-center">
        <WaveformMark className="mx-auto h-6 w-auto text-ink/20" />
        <p className="mt-3 text-sm font-medium text-ink">No memory yet</p>
        <p className="mt-1 text-xs text-ink/40">
          This conversation hasn&apos;t been processed into structured memory.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <SectionCard title="Summary">
        <p className="text-sm leading-relaxed text-ink">{memory.summary}</p>
        {memory.topics.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-1.5">
            {memory.topics.map((topic) => (
              <span
                key={topic}
                className="rounded-full bg-accent-soft px-2.5 py-1 text-xs font-medium text-accent"
              >
                {topic}
              </span>
            ))}
          </div>
        )}
        <p className="mt-4 text-xs text-ink/40">
          {Math.round(memory.confidence * 100)}% confidence · {memory.source}
        </p>
      </SectionCard>

      <div className="grid gap-4 sm:grid-cols-3">
        <SectionCard title="Decisions">
          <BulletList items={memory.decisions.map((d) => d.description)} />
        </SectionCard>
        <SectionCard title="Action Items">
          <BulletList
            items={memory.action_items.map((a) =>
              a.owner ? `${a.task} (${a.owner})` : a.task,
            )}
          />
        </SectionCard>
        <SectionCard title="People">
          <BulletList
            items={memory.people.map((p) => (p.role ? `${p.name} — ${p.role}` : p.name))}
          />
        </SectionCard>
      </div>

      {transcript?.text && (
        <div className="rounded-xl border border-line bg-surface p-6">
          <button
            type="button"
            onClick={() => setTranscriptOpen((open) => !open)}
            className="flex w-full items-center justify-between text-left"
          >
            <h3 className="text-xs font-medium uppercase tracking-wide text-ink/50">
              Transcript
            </h3>
            <span className="text-xs text-ink/40">{transcriptOpen ? "Hide" : "Show"}</span>
          </button>
          {transcriptOpen && (
            <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-ink/80">
              {transcript.text}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
