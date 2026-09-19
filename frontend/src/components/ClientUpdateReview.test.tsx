import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, expect, it, vi } from "vitest";
import { completeActionItem, reviewClientUpdates, getSavedClientReview } from "@/lib/api";
import { ClientUpdateReview } from "./ClientUpdateReview";
vi.mock("@/lib/api", () => ({ reviewClientUpdates: vi.fn(), completeActionItem: vi.fn(), getSavedClientReview: vi.fn() }));
const draft = { saved_at: "2026-09-19T09:00:00Z", conversation_count: 2, details: [{label:"Budget",value:"$375,000",quote:"Budget is $375,000",source_conversation_id:"source"}], actions: {task:"Send listings"}, completed_actions:[{action_id:"task",source_conversation_id:"source",quote:"I sent the listings"}] };
beforeEach(() => { vi.mocked(getSavedClientReview).mockResolvedValue(draft); vi.mocked(reviewClientUpdates).mockResolvedValue(draft); vi.mocked(completeActionItem).mockResolvedValue({} as never); });
function mount() { return render(<QueryClientProvider client={new QueryClient()}><ClientUpdateReview clientId="jordan" /></QueryClientProvider>); }
it("loads saved suggestions after remount without generating or completing automatically", async () => {
  const first = mount();
  expect(await screen.findByText("$375,000")).toBeInTheDocument();
  expect(reviewClientUpdates).not.toHaveBeenCalled();
  expect(completeActionItem).not.toHaveBeenCalled();
  first.unmount(); mount();
  fireEvent.click(await screen.findByText("Confirm task is complete"));
  expect(await screen.findByText("Confirmed complete")).toBeDisabled();
  expect(completeActionItem).toHaveBeenCalledWith("task");
});
it("hides stale review details and invites regeneration", async () => {
  vi.mocked(getSavedClientReview).mockResolvedValue({...draft, stale:true});
  mount();
  expect(await screen.findByRole("status")).toHaveTextContent("conversations have changed");
  expect(screen.queryByText("$375,000")).not.toBeInTheDocument();
  expect(screen.queryByText("Confirm task is complete")).not.toBeInTheDocument();
});
