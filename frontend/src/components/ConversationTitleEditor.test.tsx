import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expect, it, vi } from "vitest";
import { renameConversation } from "@/lib/api";
import { ConversationTitleEditor } from "./ConversationTitleEditor";
vi.mock("@/lib/api", () => ({renameConversation: vi.fn()}));
it("keeps failed input, retries, and refreshes dependent lists", async () => {
  vi.mocked(renameConversation).mockRejectedValueOnce(new Error("failed")).mockResolvedValueOnce(undefined);
  const client=new QueryClient(); const invalidate=vi.spyOn(client,"invalidateQueries");
  render(<QueryClientProvider client={client}><ConversationTitleEditor id="one" title="Old" /></QueryClientProvider>);
  fireEvent.click(screen.getByText("Edit title"));
  fireEvent.change(screen.getByLabelText("Conversation title"),{target:{value:"  Budget update  "}});
  fireEvent.click(screen.getByText("Save title"));
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(screen.getByLabelText("Conversation title")).toHaveValue("  Budget update  ");
  fireEvent.click(screen.getByText("Save title"));
  await waitFor(() => expect(screen.getByText("Edit title")).toBeInTheDocument());
  expect(renameConversation).toHaveBeenLastCalledWith("one","Budget update");
  expect(invalidate).toHaveBeenCalledWith({queryKey:["clients"]});
});
it("cancels without saving and prevents blank titles", () => {
  render(<QueryClientProvider client={new QueryClient()}><ConversationTitleEditor id="one" title="Old" /></QueryClientProvider>);
  fireEvent.click(screen.getByText("Edit title"));
  fireEvent.change(screen.getByLabelText("Conversation title"),{target:{value:" "}});
  expect(screen.getByText("Save title")).toBeDisabled();
  fireEvent.click(screen.getByText("Cancel"));
  expect(renameConversation).not.toHaveBeenCalled();
});
