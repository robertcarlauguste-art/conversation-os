"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { getDashboard } from "@/lib/api";
import type { DashboardOverview, DashboardPriority } from "@/lib/types";

const CARDS: { key: keyof DashboardOverview; label: string }[] = [
  { key: "clients", label: "Clients" },
  { key: "conversations", label: "Conversations" },
  { key: "processing", label: "Processing" },
  { key: "completed", label: "Completed" },
  { key: "failed", label: "Failed" },
];

const PRIORITY_STYLES: Record<DashboardPriority["severity"], string> = {
  critical: "border-red-200 bg-red-50 text-red-900",
  high: "border-amber-200 bg-amber-50 text-amber-900",
  medium: "border-line bg-paper text-ink",
};

export function SummaryCards() {
  const dashboardQuery = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
  });

  const overview = dashboardQuery.data?.overview;
  const conversations = dashboardQuery.data?.recent_conversations ?? [];
  const clients = dashboardQuery.data?.recent_clients ?? [];
  const alerts = dashboardQuery.data?.alerts ?? [];
  const followups = dashboardQuery.data?.followups ?? [];
  const priorities = dashboardQuery.data?.priorities ?? [];

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
              {overview?.[card.key] ?? 0}
            </p>
          </div>
        ))}
      </div>

      <section className="rounded-xl border border-line bg-surface p-6">
        <div>
          <h2 className="text-lg font-semibold">Executive Priorities</h2>
          <p className="mt-1 text-sm text-ink/50">
            Recommended actions ranked by urgency and relationship impact.
          </p>
        </div>

        <div className="mt-4 flex flex-col gap-3">
          {priorities.length > 0 ? (
            priorities.map((priority) => {
              const content = (
                <>
                  <span className="font-display text-2xl">{priority.rank}</span>
                  <span>
                    <span className="block font-semibold">{priority.title}</span>
                    <span className="mt-1 block text-sm opacity-70">
                      {priority.description}
                    </span>
                  </span>
                </>
              );

              const className = `grid grid-cols-[2rem_1fr] gap-3 rounded-lg border p-4 ${PRIORITY_STYLES[priority.severity]}`;

              return priority.href ? (
                <Link key={`${priority.category}-${priority.rank}`} href={priority.href} className={className}>
                  {content}
                </Link>
              ) : (
                <div key={`${priority.category}-${priority.rank}`} className={className}>
                  {content}
                </div>
              );
            })
          ) : (
            <p className="text-sm text-ink/50">No priority actions right now.</p>
          )}
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-line bg-surface p-6">
          <h2 className="text-lg font-semibold">Alerts</h2>
          <div className="mt-4 flex flex-col gap-3">
            {alerts.length > 0 ? (
              alerts.map((alert) => (
                <div
                  key={alert}
                  className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800"
                >
                  {alert}
                </div>
              ))
            ) : (
              <p className="text-sm text-ink/50">No alerts need attention.</p>
            )}
          </div>
        </section>

        <section className="rounded-xl border border-line bg-surface p-6">
          <h2 className="text-lg font-semibold">Follow-up Queue</h2>
          <div className="mt-4 flex flex-col gap-3">
            {followups.length > 0 ? (
              followups.map((followup) => (
                <div
                  key={followup}
                  className="rounded-lg border border-line bg-paper p-3 text-sm text-ink"
                >
                  {followup}
                </div>
              ))
            ) : (
              <p className="text-sm text-ink/50">No follow-ups are due.</p>
            )}
          </div>
        </section>
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
                  {conversation.title ?? "Untitled conversation"}
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
