import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { MemoryItemEditor } from "./MemoryItemEditor";
import { editMemoryItem } from "@/lib/api";

vi.mock("@/lib/api", () => ({ editMemoryItem: vi.fn() }));
const item = { id: "task", task: "Send listings", owner: "Jordan", due: "Friday", status: "OPEN", completed_at: null };
function show(action = true) {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { mutations: { retry: false } } })}><ul><MemoryItemEditor memoryId="memory" item={action ? item : { id: "decision", description: "Buy a home" }} /></ul></QueryClientProvider>);
}
it("saves task corrections including clearing optional values", async () => {
  vi.mocked(editMemoryItem).mockResolvedValue({});
  const user = userEvent.setup(); show();
  await user.click(screen.getByRole("button", { name: /Edit task/ }));
  await user.clear(screen.getByLabelText("Task"));
  await user.type(screen.getByLabelText("Task"), "Send two listings");
  await user.clear(screen.getByLabelText("Owner (optional)"));
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  await waitFor(() => expect(editMemoryItem).toHaveBeenCalledWith("memory", "task", "action-items", { task: "Send two listings", owner: null, due: "Friday" }));
  expect(await screen.findByRole("status")).toHaveTextContent("Changes saved");
});
it("keeps decision edits after a save failure and allows cancellation", async () => {
  vi.mocked(editMemoryItem).mockRejectedValue(new Error("offline"));
  const user = userEvent.setup(); show(false);
  await user.click(screen.getByRole("button", { name: /Edit decision/ }));
  await user.clear(screen.getByLabelText("Decision"));
  await user.type(screen.getByLabelText("Decision"), "Wait until next year");
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("edits are still here");
  expect(screen.getByLabelText("Decision")).toHaveValue("Wait until next year");
  await user.click(screen.getByRole("button", { name: "Cancel" }));
  expect(screen.getByText("Buy a home")).toBeInTheDocument();
});
