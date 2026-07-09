import type { ConversationStatus } from "@/lib/types";

const LABELS: Record<ConversationStatus, string> = {
  UPLOADED: "Uploaded",
  QUEUED: "Queued",
  PROCESSING: "Processing",
  COMPLETED: "Completed",
  FAILED: "Failed",
};

const DOT_COLOR: Record<ConversationStatus, string> = {
  UPLOADED: "bg-status-uploaded",
  QUEUED: "bg-status-queued",
  PROCESSING: "bg-status-processing",
  COMPLETED: "bg-status-completed",
  FAILED: "bg-status-failed",
};

export function StatusBadge({ status }: { status: ConversationStatus }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-2.5 py-1 text-xs font-medium text-ink">
      <span className={`h-1.5 w-1.5 rounded-full ${DOT_COLOR[status]}`} />
      {LABELS[status]}
    </span>
  );
}
