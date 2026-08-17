"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { listClients, listConversations } from "@/lib/api";
import type { ConversationStatus } from "@/lib/types";

const CARDS: { key: ConversationStatus | "TOTAL" | "CLIENTS"; label: string }[] = [
  { key: "CLIENTS", label: "Clients" },
  { key: "TOTAL", label: "Conversations" },
  { key: "PROCESSING", label: "Processing" },
  { key: "COMPLETED", label: "Completed" },
  { key: "FAILED", label: "Failed" },
];

export function SummaryCards() {
  const conversationsQuery = useQuery({
    queryKey: ["conversations"],
    queryFn: listConversations,
  });

  const clientsQuery = useQuery({
    queryKey: ["clients"],
    queryFn: listClients,
  });

  const conversations = conversationsQuery.data ?? [];
  const clients = clientsQuery.data ?? [];

  const counts: Record<string, number> = {
    CLIENTS: clients.length,
    TOTAL: conversations.length,
  };

  for (const status of [
    "UPLOADED",
    "QUEUED",
    "PROCESSING",
    "COMPLETED",
    "FAILED",
  ]) {
    counts[status] =
      conversations.filter((c) => c.status === status).length;
  }

  return (
    <div className="flex flex-col gap-8">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {CARDS.map((card) => (
          <div
            key={card.key}
            className="rounded-xl border border-line bg-surface p-5"
          >
            <p className="text-xs font-medium uppercase tracking-wide text-ink/50">
              {card.label}
            </p>

            <p className="mt-2 font-display text-3xl text-ink">
              {counts[card.key] ?? 0}
            </p>
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-line bg-surface p-6">
          <h2 className="text-lg font-semibold">Recent Conversations</h2>

          <div className="mt-4 flex flex-col gap-3">
            {conversations.slice(0, 5).map((conversation) => (
              <Link
                key={conversation.id}
                href={`/conversations/${conversation.id}`}
                className="flex items-center justify-between rounded-lg border border-line p-3 hover:bg-paper"
              >
                <span>
                  {conversation.title ?? conversation.filename}
                </span>

                <span className="text-xs text-ink/50">
                  {conversation.status}
                </span>
              </Link>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-line bg-surface p-6">
          <h2 className="text-lg font-semibold">Recent Clients</h2>

          <div className="mt-4 flex flex-col gap-3">
            {clients.slice(0, 5).map((client) => (
              <Link
                key={client.id}
                href={`/clients/${client.id}`}
                className="rounded-lg border border-line p-3 hover:bg-paper"
              >
                <div className="font-medium">
                  {client.full_name}
                </div>

                <div className="text-sm text-ink/50">
                  {client.email ?? "No email"}
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}