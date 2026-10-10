"use client";
import { useLanguage } from "@/components/LanguageProvider";
import { TranscriptCorrectionEditor } from "./TranscriptCorrectionEditor";
import { ConversationTasks } from "./ConversationTasks";
import { PrepareFollowup } from "./PrepareFollowup";
import { PersonConfirmation } from "./PersonConfirmation";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { getMemoryByConversation, getTranscriptByConversation } from "@/lib/api";
import type { ConversationStatus } from "@/lib/types";
import { WaveformMark } from "./WaveformMark";
import { MemoryItemEditor } from "./MemoryItemEditor";

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-6">
      <h3 className="font-display text-xl text-ink">{title}</h3>
      <div className="mt-3">{children}</div>
    </div>
  );
}

function EmptyNote({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-ink/40">{children}</p>;
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
  const { t } = useLanguage();
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
        <p className="text-sm font-medium text-status-failed">{t("Processing failed")}</p>
        <p className="mt-1 text-xs text-ink/50">
          {processingError ??
            t("Transcription or extraction didn't complete for this conversation.")}
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
        <p className="mt-3 text-sm font-medium text-ink">{t("Processing conversation…")}</p>
        <p className="mt-1 text-xs text-ink/40">{" "}{t("Transcribing, then extracting summary and key details.")}{" "}</p>
      </div>
    );
  }

  if (memoryQuery.isError) {
    return (
      <div className="rounded-xl border border-status-failed/30 bg-surface p-6 text-center">
        <p className="text-sm text-status-failed">{" "}{t("Couldn't load this conversation's memory. Please refresh the page and try again.")}{" "}</p>
      </div>
    );
  }

  const memory = memoryQuery.data;
  const transcript = transcriptQuery.data;

  if (!memory) {
    return (
      <div className="rounded-xl border border-dashed border-line bg-surface py-12 text-center">
        <WaveformMark className="mx-auto h-6 w-auto text-ink/20" />
        <p className="mt-3 text-sm font-medium text-ink">{t("No memory yet")}</p>
        <p className="mt-1 text-xs text-ink/40">{" "}{t("This conversation hasn't been processed into structured memory.")}{" "}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <SectionCard title={t("Summary")}>
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
        <p className="mt-4 text-xs text-ink/40">{" "}{t("AI-generated summary. Check important details and follow-up actions against the transcript; AI can make mistakes.")}{" "}</p>
      </SectionCard>

      <PrepareFollowup key={conversationId} conversationId={conversationId} memory={memory} />
        <SectionCard title={t("Tasks to review")}>
          <ConversationTasks memoryId={memory.id} items={memory.action_items} />
        </SectionCard>
      <div className="grid gap-4 sm:grid-cols-2">
        <SectionCard title={t("Decisions")}>
          {memory.decisions.length ? <ul className="flex flex-col gap-3">{memory.decisions.map(item => <MemoryItemEditor key={item.id} memoryId={memory.id} item={item} />)}</ul> : <EmptyNote>{t("None identified.")}</EmptyNote>}
        </SectionCard>

        <SectionCard title={t("People")}>
          {memory.people.length ? <ul className="space-y-3">{memory.people.map(p => <PersonConfirmation key={p.id} memoryId={memory.id} person={p} />)}</ul> : <EmptyNote>{t("None identified.")}</EmptyNote>}
        </SectionCard>
      </div>

      {transcript?.text && (
        <div className="rounded-xl border border-line bg-surface p-6">
          <button
            type="button"
            aria-expanded={transcriptOpen}
            aria-controls="conversation-transcript"
            onClick={() => setTranscriptOpen((open) => !open)}
            className="flex w-full items-center justify-between text-left"
          >
            <h3 className="text-xs font-medium uppercase tracking-wide text-ink/50">{" "}{t("Transcript")}{" "}</h3>
            <span className="text-xs text-ink/40">{transcriptOpen ? t("Hide") : t("Show")}</span>
          </button>
          {(
            <div hidden={!transcriptOpen}><p className="mt-3 font-medium">{t("Original transcript")}</p><p id="conversation-transcript" className="mt-3 break-words whitespace-pre-wrap text-sm leading-relaxed text-ink/80">
              {transcript.text}</p><TranscriptCorrectionEditor conversationId={conversationId} original={transcript.text} /></div>
          )}
        </div>
      )}
    </div>
  );
}
