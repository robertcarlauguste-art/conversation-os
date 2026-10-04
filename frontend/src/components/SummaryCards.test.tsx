import { LanguageProvider, LanguageSelector } from "./LanguageProvider";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { DashboardData } from "@/lib/types";
import { ToastProvider } from "./Toast";
import { SummaryCards } from "./SummaryCards";

const api = vi.hoisted(() => ({
  completeActionItem: vi.fn(),
  generateDashboardBriefing: vi.fn(),
  getDashboard: vi.fn(),
  recordFollowupAction: vi.fn(),
  reopenActionItem: vi.fn(),
}));

vi.mock("@/lib/api", () => api);

const dashboard: DashboardData = {
  overview: {
    clients: 1,
    conversations: 2,
    queued: 0,
    stale: 0,
    processing: 0,
    completed: 2,
    failed: 0,
  },
  recent_clients: [],
  recent_conversations: [],
  daily_brief: [],
  priorities: [],
  client_recommendations: [
    {
      rank: 1,
      client_id: "client-1",
      client_name: "John Buyer",
      urgency_score: 75,
      reason: "Last conversation was 10 days ago.",
      recommended_action: "Follow up today.",
      days_since_contact: 10,
      conversation_count: 2,
      open_action_count: 2,
      href: "/clients/client-1",
    },
  ],
  next_actions: [
    {
      id: "action-1",
      action_item_ids: ["action-1", "action-2"],
      source_count: 2,
      task: "Schedule a home showing",
      due: "next Tuesday",
      owner: "Sarah",
      client_id: "client-1",
      client_name: "John Buyer",
      conversation_id: "conversation-1",
      conversation_title: "Buyer consultation",
      href: "/conversations/conversation-1",
    },
  ],
  recent_activity: [
    {
      id: "completed-1",
      client_id: "client-1",
      client_name: "John Buyer",
      action: "complete_action_item",
      description: 'Completed action item "Send listings".',
      occurred_at: "2026-08-18T12:00:00Z",
      snoozed_until: null,
      href: "/conversations/conversation-1",
    },
  ],
  alerts: [],
  followups: [],
};

function renderDashboard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <SummaryCards />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe("SummaryCards interactions", () => {
  it("leads with tasks and hides technical count cards while retaining alerts", async () => {
    api.getDashboard.mockResolvedValue({
      ...dashboard,
      overview: { ...dashboard.overview, queued: 4, stale: 2 },
      alerts: ["2 conversations are possibly stalled. Review the conversation list."],
    });
    renderDashboard();
    await screen.findByRole("heading", { name: "Tasks needing attention" });
    expect(screen.queryByText("Queued")).not.toBeInTheDocument();
    expect(screen.queryByText("Possibly stalled")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Tasks needing attention" })).toBeVisible();
    expect(screen.getByText("Client follow-ups").closest("details")).not.toHaveAttribute("open");
    expect(screen.getByText("Activity & completed tasks").closest("details")).not.toHaveAttribute("open");
    expect(screen.getByText(/2 conversations are possibly stalled/)).toBeInTheDocument();
  });

  beforeEach(() => {
    api.getDashboard.mockResolvedValue(dashboard);
    api.completeActionItem.mockResolvedValue({});
    api.recordFollowupAction.mockResolvedValue({});
    api.reopenActionItem.mockResolvedValue({});
  });

  it("records client contact and confirms success", async () => {
    const user = userEvent.setup();
    renderDashboard();

    await user.click(await screen.findByText("Client follow-ups"));
    await user.click(await screen.findByText("Why follow up & actions"));
    await user.click(await screen.findByRole("button", { name: "Record contact" }));

    await waitFor(() =>
      expect(api.recordFollowupAction).toHaveBeenCalledWith(
        "client-1",
        "record_contact",
        undefined,
      ),
    );
    expect(await screen.findByRole("status")).toHaveTextContent("Follow-up updated.");
  });

  it("completes every source item in an identical group", async () => {
    const user = userEvent.setup();
    renderDashboard();

    await user.click(await screen.findByRole("button", { name: "Complete all 2" }));

    await waitFor(() => expect(api.completeActionItem).toHaveBeenCalledTimes(2));
    expect(api.completeActionItem).toHaveBeenCalledWith("action-1");
    expect(api.completeActionItem).toHaveBeenCalledWith("action-2");
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Action item completed.",
    );
  });

  it("reopens a completed action from recent activity", async () => {
    const user = userEvent.setup();
    renderDashboard();

    await user.click(await screen.findByText("Activity & completed tasks"));
    await user.click(await screen.findByRole("button", { name: "Reopen" }));

    await waitFor(() =>
      expect(api.reopenActionItem).toHaveBeenCalledWith("completed-1"),
    );
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Action item reopened.",
    );
  });
});

it("translates controls without translating saved tasks or generating a briefing", async () => {
  localStorage.clear();
  api.getDashboard.mockResolvedValue(dashboard);
  const user = userEvent.setup();
  render(<LanguageProvider><LanguageSelector /><QueryClientProvider client={new QueryClient()}><ToastProvider><SummaryCards /></ToastProvider></QueryClientProvider></LanguageProvider>);
  await screen.findByText("Tasks needing attention");
  await user.selectOptions(screen.getByLabelText("Language / Lang"), "ht");
  expect(screen.getByText("Travay pou ou verifye")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Prepare rezime a" })).toBeInTheDocument();
  expect(screen.getByText("Schedule a home showing")).toBeInTheDocument();
  expect(screen.getByText(/Sarah/)).toBeInTheDocument();
  expect(api.generateDashboardBriefing).not.toHaveBeenCalled();
  localStorage.clear();
});

