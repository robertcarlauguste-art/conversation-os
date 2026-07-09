"use client";

import { useQuery } from "@tanstack/react-query";
import { listConversations } from "@/lib/api";
import type { ConversationStatus } from "@/lib/types";

const CARDS: { key: ConversationStatus | "TOTAL"; label: string }[] = [
  { key: "TOTAL", label: "Total Conversations" },
  { key: "UPLOADED", label: "Uploaded" },
  { key: "PROCESSING", label: "Processing" },
  { key: "COMPLETED", label: "Completed" },
  { key: "FAILED", label: "Failed" },
];

export function SummaryCards() {
  const { data } = useQuery({
    queryKey: ["conversations"],
    queryFn: listConversations,
  });

  const counts: Record<string, number> = { TOTAL: data?.length ?? 0 };
  for (const status of ["UPLOADED", "QUEUED", "PROCESSING", "COMPLETED", "FAILED"]) {
    counts[status] = data?.filter((c) => c.status === status).length ?? 0;
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
      {CARDS.map((card) => (
        <div key={card.key} className="rounded-xl border border-line bg-surface p-5">
          <p className="text-xs font-medium uppercase tracking-wide text-ink/50">{card.label}</p>
          <p className="mt-2 font-display text-3xl text-ink">{counts[card.key] ?? 0}</p>
        </div>
      ))}
    </div>
  );
}
