import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expect, it, vi } from "vitest";
import { completeActionItem, reviewClientUpdates } from "@/lib/api";
import { ClientUpdateReview } from "./ClientUpdateReview";
vi.mock("@/lib/api", () => ({ reviewClientUpdates: vi.fn(), completeActionItem: vi.fn() }));
it("generates on request and completes only after explicit review confirmation", async () => {
  vi.mocked(reviewClientUpdates).mockResolvedValue({ conversation_count: 2, details: [{label:"Budget",value:"$375,000",quote:"Budget is $375,000",source_conversation_id:"source"}], actions: {task:"Send listings"}, completed_actions:[{action_id:"task",source_conversation_id:"source",quote:"I sent the listings"}] });
  vi.mocked(completeActionItem).mockResolvedValue({} as never);
  render(<QueryClientProvider client={new QueryClient()}><ClientUpdateReview clientId="jordan" /></QueryClientProvider>);
  expect(reviewClientUpdates).not.toHaveBeenCalled();
  fireEvent.click(screen.getByText("Review client updates"));
  expect(await screen.findByText("$375,000")).toBeInTheDocument();
  expect(completeActionItem).not.toHaveBeenCalled();
  fireEvent.click(screen.getByText("Confirm task is complete"));
  await waitFor(() => expect(completeActionItem).toHaveBeenCalledWith("task"));
  expect(await screen.findByText("Confirmed complete")).toBeDisabled();
});
