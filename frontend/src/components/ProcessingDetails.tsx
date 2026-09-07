import type { ConversationDetail } from "@/lib/types";

export function ProcessingDetails({
  conversation: c,
}: {
  conversation: ConversationDetail;
}) {
  const timestamp = (value: string | null) =>
    value ? new Date(value).toLocaleString() : "Not recorded";
  return (
    <section
      className="rounded-xl border border-line bg-surface p-6"
      aria-label="Processing details"
    >
      <h2 className="text-lg font-semibold">Processing details</h2>
      <dl className="mt-3 grid gap-3 sm:grid-cols-2">
        <div>
          <dt>Attempts</dt>
          <dd>{c.processing_attempts}</dd>
        </div>
        <div>
          <dt>Queued / received (approximate)</dt>
          <dd>{timestamp(c.created_at)}</dd>
        </div>
        <div>
          <dt>Latest attempt started</dt>
          <dd>{timestamp(c.processing_started_at)}</dd>
        </div>
        <div>
          <dt>{c.status === "FAILED" ? "Failed" : "Completed"}</dt>
          <dd>{timestamp(c.processing_completed_at)}</dd>
        </div>
      </dl>
      {c.processing_error && (
        <p className="mt-3 text-status-failed">
          Latest error: {c.processing_error}
        </p>
      )}
      {c.is_stale && (
        <p role="status" className="mt-3 text-amber-700">
          Possibly stalled: this job has exceeded{" "}
          {Math.round(c.stale_threshold_seconds / 60)} minutes in its current
          stage. Check worker availability. Timing alone does not confirm
          abandonment.
        </p>
      )}
    </section>
  );
}
