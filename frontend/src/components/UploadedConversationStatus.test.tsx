import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { getConversation } from "@/lib/api";
import { UploadedConversationStatus } from "./UploadedConversationStatus";

vi.mock("@/lib/api", () => ({ getConversation: vi.fn() }));
function setup() {
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  cache.setQueryData(["conversations", "list", 1], {status:"QUEUED"});
  cache.setQueryData(["dashboard"], {queued:1});
  render(<QueryClientProvider client={cache}><UploadedConversationStatus id="mine" /></QueryClientProvider>);
  return cache;
}
it("polls until ready and then stops, with a direct results link", async () => {
  vi.mocked(getConversation).mockResolvedValueOnce({status:"PROCESSING"} as never).mockResolvedValue({status:"COMPLETED"} as never);
  const cache = setup();
  await waitFor(() => expect(getConversation).toHaveBeenCalledTimes(1));
  expect(screen.getByText(/Preparing your notes/)).toBeInTheDocument();
  expect(await screen.findByRole("link", {name:"View summary and tasks"}, {timeout:5000})).toHaveAttribute("href", "/conversations/mine");
  await act(async () => { await new Promise(resolve => setTimeout(resolve, 3200)); });
  expect(getConversation).toHaveBeenCalledTimes(2);
  expect(cache.getQueryState(["conversations", "list", 1])?.isInvalidated).toBe(true);
  expect(cache.getQueryState(["dashboard"])?.isInvalidated).toBe(true);
  expect(cache.getQueryState(["conversations", "mine"])?.isInvalidated).toBe(false);
});
it("offers a manual status retry without exposing server errors", async () => {
  vi.mocked(getConversation).mockRejectedValueOnce(new Error("private server detail")).mockResolvedValue({status:"COMPLETED"} as never);
  setup();
  await screen.findByText(/Status temporarily unavailable/);
  expect(screen.queryByText(/private server detail/)).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", {name:"Check again"}));
  await screen.findByRole("link", {name:"View summary and tasks"});
});
it("explains a processing failure without claiming results are ready", async () => {
  vi.mocked(getConversation).mockResolvedValue({status:"FAILED"} as never);
  setup();
  await screen.findByText("We couldn’t prepare your notes.");
  expect(screen.getByRole("link", {name:"Open your conversation"})).toHaveAttribute("href", "/conversations/mine");
  expect(screen.queryByRole("link", {name:"View summary and tasks"})).not.toBeInTheDocument();
});
