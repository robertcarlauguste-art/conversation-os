import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { ConversationsTable } from "./ConversationsTable";
vi.mock("@/lib/api", () => ({ listConversations: vi.fn(async (options) => options.search ? [] : [{ id: "c", title: "Jordan note", status: "COMPLETED", file_size: 100, created_at: "2026-09-22T12:00:00Z" }]), deleteConversation: vi.fn() }));
it("keeps search controls available after no matches and lets the user recover", async () => {
  const user = userEvent.setup();
  render(<QueryClientProvider client={new QueryClient()}><ConversationsTable /></QueryClientProvider>);
  await screen.findByText("Jordan note");
  await user.type(screen.getByLabelText("Search conversations"), "missing");
  await screen.findByText("No conversations match these filters.");
  expect(screen.queryByText("No conversations yet")).not.toBeInTheDocument();
  await user.clear(screen.getByLabelText("Search conversations"));
  expect(await screen.findByText("Jordan note")).toBeInTheDocument();
});
