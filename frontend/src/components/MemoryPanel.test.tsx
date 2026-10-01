import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expect, it, vi } from "vitest";
import { MemoryPanel } from "./MemoryPanel";
vi.mock("@/lib/api", () => ({
  getSavedFollowup: vi.fn(async () => null),
  getMemoryByConversation: vi.fn(async () => ({ summary: "Jordan wants a home.", topics: [], confidence: 0.9, source: "model", decisions: [], action_items: [], people: [] })),
  getTranscriptByConversation: vi.fn(async () => ({ text: "Original words" })),
}));
it("prompts verification without presenting model confidence as measured accuracy", async () => {
  render(<QueryClientProvider client={new QueryClient()}><MemoryPanel conversationId="test" status="COMPLETED" /></QueryClientProvider>);
  expect(await screen.findByText(/Check important details/)).toBeInTheDocument();
  expect(screen.queryByText(/90%/)).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Transcript/ })).toBeInTheDocument();
});
