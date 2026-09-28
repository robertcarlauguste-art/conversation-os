"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  generateDashboardBriefing,
  completeActionItem,
  getDashboard,
  recordFollowupAction,
  reopenActionItem,
} from "@/lib/api";
import type {
  DashboardBriefItem,
  DashboardOverview,
} from "@/lib/types";
import { conversationTitle, formatDate } from "@/lib/format";
import { useToast } from "./Toast";

const CARDS: { key: keyof DashboardOverview; label: string }[] = [
  { key: "clients", label: "Clients" },
  { key: "conversations", label: "Conversations" },

];

const BRIEF_MARKERS: Record<DashboardBriefItem["tone"], string> = {
  neutral: "bg-ink/30",
  positive: "bg-emerald-500",
  warning: "bg-amber-500",
};

function DashboardSkeleton() {
  return (
    <div aria-label="Loading dashboard" className="flex animate-pulse flex-col gap-8">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {CARDS.map((card) => (
          <div key={card.key} className="h-28 rounded-xl bg-ink/5" />
        ))}
      </div>
      <div className="h-40 rounded-xl bg-ink/5" />
      <div className="h-64 rounded-xl bg-ink/5" />
      <span className="sr-only">Loading dashboard data...</span>
    </div>
  );
}

export function SummaryCards() {
  const queryClient = useQueryClient();
  const { notify } = useToast();
  const dashboardQuery = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
  });
  const briefingMutation = useMutation({
    mutationFn: generateDashboardBriefing,
  });
  const followupMutation = useMutation({
    mutationFn: ({
      clientId,
      action,
      snoozeDays,
    }: {
      clientId: string;
      action: "complete" | "snooze" | "record_contact";
      snoozeDays?: number;
    }) => recordFollowupAction(clientId, action, snoozeDays),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      notify("Follow-up updated.", "success");
    },
  });
  const actionItemMutation = useMutation({
    mutationFn: async (actionItemIds: string[]) => {
      await Promise.all(
        actionItemIds.map((actionItemId) => completeActionItem(actionItemId)),
      );
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      notify("Action item completed.", "success");
    },
  });
  const reopenActionMutation = useMutation({
    mutationFn: reopenActionItem,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      notify("Action item reopened.", "success");
    },
  });

  const overview = dashboardQuery.data?.overview;
  const conversations = dashboardQuery.data?.recent_conversations ?? [];
  const clients = dashboardQuery.data?.recent_clients ?? [];
  const alerts = dashboardQuery.data?.alerts ?? [];
  const clientRecommendations = dashboardQuery.data?.client_recommendations ?? [];
  const nextActions = dashboardQuery.data?.next_actions ?? [];
  const recentActivity = dashboardQuery.data?.recent_activity ?? [];
  const dailyBrief = dashboardQuery.data?.daily_brief ?? [];

  if (dashboardQuery.isPending) {
    return <DashboardSkeleton />;
  }

  if (dashboardQuery.isError) {
    return (
      <section
        role="alert"
        className="rounded-xl border border-red-200 bg-red-50 p-6 text-red-900"
      >
        <h2 className="text-lg font-semibold">Dashboard unavailable</h2>
        <p className="mt-2 text-sm text-red-800">
          {dashboardQuery.error instanceof Error
            ? dashboardQuery.error.message
            : "ConversationOS could not load your dashboard."}
        </p>
        <button
          type="button"
          onClick={() => void dashboardQuery.refetch()}
          disabled={dashboardQuery.isFetching}
          className="mt-4 rounded-lg bg-red-800 px-4 py-2 text-sm font-medium text-white disabled:cursor-wait disabled:opacity-60"
        >
          {dashboardQuery.isFetching ? "Retrying..." : "Try again"}
        </button>
      </section>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      {alerts.length > 0 ? (
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


      </div>      ) : null}
      <section className="rounded-xl border border-line bg-surface p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold">AI briefing</h2>
            <p className="mt-1 text-sm text-ink/50">
              A concise synthesis generated only when you request it.
            </p>
          </div>
          <button
            type="button"
            onClick={() => briefingMutation.mutate()}
            disabled={briefingMutation.isPending}
            className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-white disabled:cursor-wait disabled:opacity-60"
          >
            {briefingMutation.isPending
              ? "Generating..."
              : briefingMutation.data
                ? "Regenerate briefing"
                : "Generate briefing"}
          </button>
        </div>

        {briefingMutation.isError ? (
          <div
            role="alert"
            className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4"
          >
            <p className="text-sm text-red-800">
              {briefingMutation.error instanceof Error
                ? briefingMutation.error.message
                : "The briefing could not be generated."}
            </p>
          </div>
        ) : null}

        {briefingMutation.data ? (
          <div className="mt-4 rounded-lg border border-line bg-paper p-5">
            <p className="leading-7 text-ink">{briefingMutation.data.content}</p>
            <p className="mt-3 text-xs uppercase tracking-wide text-ink/40">
              {briefingMutation.data.source === "ai"
                ? `AI generated${
                    briefingMutation.data.model
                      ? ` · ${briefingMutation.data.model}`
                      : ""
                  }`
                : "Deterministic fallback"}
            </p>
          </div>
        ) : null}
      </section>

      <section className="rounded-xl border border-line bg-surface p-6">
        <div>
          <h2 className="text-lg font-semibold">Tasks needing attention</h2>
          <p className="mt-1 text-sm text-ink/50">
            Review, edit, and complete tasks from your conversations. Open a task to see its recording and edit the details.
          </p>
        </div>

        <div className="mt-4 flex flex-col gap-3">
          {nextActions.length > 0 ? (
            nextActions.map((action) => (
              <div
                key={action.id}
                className="grid gap-3 rounded-lg border border-line bg-paper p-4 sm:grid-cols-[1fr_auto] sm:items-center"
              >
                <span>
                  <Link href={action.href} className="block font-medium hover:underline">
                    {action.task}
                  </Link>
                  <span className="mt-1 block text-sm text-ink/50">
                    {action.client_name ??
                      action.conversation_title ??
                      "Unassigned conversation"}
                    {action.owner ? ` · Owner: ${action.owner}` : ""}
                    {action.source_count > 1
                      ? ` · ${action.source_count} identical source items`
                      : ""}
                  </span>
                </span>
                <span className="flex flex-col items-start gap-2 sm:items-end">
                  <span className="text-sm text-ink/50">
                    {action.due ? `Due ${action.due}` : "No due date"}
                  </span>
                  <button
                    type="button"
                    disabled={actionItemMutation.isPending}
                    onClick={() => actionItemMutation.mutate(action.action_item_ids)}
                    className="rounded-md bg-ink px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
                  >
                    {action.source_count > 1
                      ? `Complete all ${action.source_count}`
                      : "Complete"}
                  </button>
                </span>
              </div>
            ))
          ) : (
            <p className="text-sm text-ink/50">
              No open conversation actions need attention.
            </p>
          )}
        </div>
        {actionItemMutation.isError ? (
          <p role="alert" className="mt-3 text-sm text-red-700">
            {actionItemMutation.error instanceof Error
              ? actionItemMutation.error.message
              : "The action item could not be completed."}
          </p>
        ) : null}
      </section>
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-line bg-surface p-6">
          <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-lg font-semibold">Recent conversations</h2><Link href="/conversations" className="text-sm text-accent underline">View all conversations</Link></div>

          <div className="mt-4 flex flex-col gap-3">
            {conversations.length > 0 ? (
              conversations.slice(0, 5).map((conversation) => (
                <Link
                  key={conversation.id}
                  href={`/conversations/${conversation.id}`}
                  className="flex flex-col gap-2 rounded-lg border border-line p-4 hover:bg-paper sm:flex-row sm:items-center sm:justify-between"
                >
                  <span className="min-w-0 break-words font-medium">{conversationTitle(conversation)}</span>
                  <span className="text-xs text-ink/50">{({ COMPLETED: "Ready to review", QUEUED: "Waiting to start", UPLOADED: "Waiting to start", PROCESSING: "Preparing your notes", FAILED: "Needs attention" })[conversation.status]}</span>
                </Link>
              ))
            ) : (
              <p className="text-sm text-ink/50">
                Record or upload your first conversation to see it here.
              </p>
            )}
          </div>
        </div>

        <div className="rounded-xl border border-line bg-surface p-6">
          <h2 className="text-lg font-semibold">Recent clients</h2>

          <div className="mt-4 flex flex-col gap-3">
            {clients.length > 0 ? (
              clients.slice(0, 5).map((client) => (
                <Link
                  key={client.id}
                  href={`/clients/${client.id}`}
                  className="rounded-lg border border-line p-3 hover:bg-paper"
                >
                  <div className="font-medium">{client.full_name}</div>
                  <div className="text-sm text-ink/50">
                    {client.email ?? "No email"}
                  </div>
                </Link>
              ))
            ) : (
              <p className="text-sm text-ink/50">
                Clients will appear after conversation processing identifies them.
              </p>
            )}
          </div>
        </div>
      </div>

      <details className="rounded-xl border border-line bg-surface p-4">
        <summary className="cursor-pointer py-2 font-semibold">Client follow-ups</summary>
      <section className="rounded-xl border border-line bg-surface p-6">
        <div>
          <h2 className="text-lg font-semibold">Suggested client follow-ups</h2>
          <p className="mt-1 text-sm text-ink/50">
            Suggested follow-ups based on your conversations. Review what matters today.
          </p>
        </div>

        <div className="mt-4 flex flex-col gap-3">
          {clientRecommendations.length > 0 ? (
            clientRecommendations.map((recommendation) => (
              <div
                key={recommendation.client_id}
                className="rounded-lg border border-line bg-paper p-3 hover:border-ink/30"
              >
                <span>
                  <Link
                    href={recommendation.href}
                    className="block font-semibold hover:underline"
                  >
                    {recommendation.client_name}
                  </Link>
                </span>
                <details className="mt-2 text-sm">
                  <summary className="cursor-pointer py-1 text-ink/60">Why follow up & actions</summary>
                  <p className="my-3 text-ink/60">{recommendation.reason} {recommendation.recommended_action}</p>
                  <span className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={followupMutation.isPending}
                      onClick={() =>
                        followupMutation.mutate({
                          clientId: recommendation.client_id,
                          action: "record_contact",
                        })
                      }
                      className="rounded-md bg-ink px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
                    >
                      Record contact
                    </button>
                    <button
                      type="button"
                      disabled={followupMutation.isPending}
                      onClick={() =>
                        followupMutation.mutate({
                          clientId: recommendation.client_id,
                          action: "snooze",
                          snoozeDays: 1,
                        })
                      }
                      className="rounded-md border border-line bg-surface px-3 py-1.5 text-xs font-medium disabled:opacity-50"
                    >
                      Snooze 1 day
                    </button>
                    <button
                      type="button"
                      disabled={followupMutation.isPending}
                      onClick={() =>
                        followupMutation.mutate({
                          clientId: recommendation.client_id,
                          action: "complete",
                        })
                      }
                      className="rounded-md border border-line bg-surface px-3 py-1.5 text-xs font-medium disabled:opacity-50"
                    >
                      Complete
                    </button>
                  </span>
                </details>
              </div>
            ))
          ) : (
            <p className="text-sm text-ink/50">
              No client follow-ups are due right now.
            </p>
          )}
        </div>
        {followupMutation.isError ? (
          <p role="alert" className="mt-3 text-sm text-red-700">
            {followupMutation.error instanceof Error
              ? followupMutation.error.message
              : "The follow-up action could not be saved."}
          </p>
        ) : null}
      </section>
      </details>

      <details className="rounded-xl border border-line bg-surface p-4">
        <summary className="cursor-pointer py-2 font-semibold">Activity & completed tasks</summary>
        <div className="mt-4 flex flex-col gap-6">
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

      <details className="rounded-xl border border-line bg-surface p-4">
        <summary className="cursor-pointer text-sm">Activity overview</summary>
      <section className="rounded-xl border border-line bg-surface p-6">
        <h2 className="text-lg font-semibold">Today&apos;s Brief</h2>
        <p className="mt-1 text-sm text-ink/50">
          A concise view of what happened and what needs attention.
        </p>

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {dailyBrief.length > 0 ? (
            dailyBrief.map((item) => (
              <div key={item.category} className="flex items-start gap-3 rounded-lg bg-paper p-3">
                <span
                  aria-hidden="true"
                  className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${BRIEF_MARKERS[item.tone]}`}
                />
                <span className="text-sm leading-5 text-ink">{item.text}</span>
              </div>
            ))
          ) : (
            <p className="text-sm text-ink/50">No briefing data is available yet.</p>
          )}
        </div>
      </section>
      </details>



      <section className="rounded-xl border border-line bg-surface p-6">
        <div>
          <h2 className="text-lg font-semibold">Recent Activity</h2>
          <p className="mt-1 text-sm text-ink/50">
            A durable history of follow-up decisions and recorded contact.
          </p>
        </div>

        <div className="mt-4 flex flex-col gap-3">
          {recentActivity.length > 0 ? (
            recentActivity.map((activity) => (
              <div
                key={`${activity.action}-${activity.id}`}
                className="grid gap-3 rounded-lg border border-line bg-paper p-4 sm:grid-cols-[1fr_auto] sm:items-center"
              >
                <span>
                  <Link
                    href={activity.href}
                    className="block text-sm font-medium hover:underline"
                  >
                    {activity.description}
                  </Link>
                  {activity.snoozed_until ? (
                    <span className="mt-1 block text-xs text-ink/50">
                      Snoozed until {formatDate(activity.snoozed_until)}
                    </span>
                  ) : null}
                </span>
                <span className="flex flex-col items-start gap-2 sm:items-end">
                  <span className="text-xs text-ink/50">
                    {formatDate(activity.occurred_at)}
                  </span>
                  {activity.action === "complete_action_item" ? (
                    <button
                      type="button"
                      disabled={reopenActionMutation.isPending}
                      onClick={() => reopenActionMutation.mutate(activity.id)}
                      className="rounded-md border border-line bg-surface px-3 py-1.5 text-xs font-medium disabled:opacity-50"
                    >
                      Reopen
                    </button>
                  ) : null}
                </span>
              </div>
            ))
          ) : (
            <p className="text-sm text-ink/50">
              Follow-up activity will appear after you take an action.
            </p>
          )}
        </div>
        {reopenActionMutation.isError ? (
          <p role="alert" className="mt-3 text-sm text-red-700">
            {reopenActionMutation.error instanceof Error
              ? reopenActionMutation.error.message
              : "The action item could not be reopened."}
          </p>
        ) : null}
      </section>





        </div>
      </details>



    </div>
  );
}
