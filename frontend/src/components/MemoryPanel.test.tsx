import { fireEvent, render, screen, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, expect, it, vi } from "vitest";
import { MemoryPanel } from "./MemoryPanel";
import { LanguageProvider, LanguageSelector } from "./LanguageProvider";
import { translate } from "@/lib/onboarding-translations";
import { getMemoryByConversation, getTranscriptByConversation } from "@/lib/api";
afterEach(() => localStorage.clear());
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
it("renders distinct real section empty states while preserving loaded content across languages", async () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><LanguageProvider><LanguageSelector /><MemoryPanel conversationId="test" status="COMPLETED" /></LanguageProvider></QueryClientProvider>);
  await screen.findByText("Jordan wants a home.");
  const memoryReads = vi.mocked(getMemoryByConversation).mock.calls.length;
  const transcriptReads = vi.mocked(getTranscriptByConversation).mock.calls.length;
  for (const language of ["en", "ht", "fr", "es"] as const) {
    fireEvent.change(screen.getByLabelText("Language / Lang"), { target: { value: language } });
    const decisions = screen.getByRole("heading", { name: translate(language, "Decisions") }).parentElement!;
    const people = screen.getByRole("heading", { name: translate(language, "People") }).parentElement!;
    expect(within(decisions).getByText(translate(language, "No decisions identified."))).toBeInTheDocument();
    expect(within(people).getByText(translate(language, "No people identified."))).toBeInTheDocument();
    expect(screen.getAllByText("Jordan wants a home.").length).toBeGreaterThan(0);
    expect(screen.getByText("Original words")).toBeInTheDocument();
  }
  expect(vi.mocked(getMemoryByConversation).mock.calls.length).toBe(memoryReads);
  expect(vi.mocked(getTranscriptByConversation).mock.calls.length).toBe(transcriptReads);
  client.clear();
});
