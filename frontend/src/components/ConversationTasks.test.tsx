import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { ConversationTasks } from "./ConversationTasks";
import { completeActionItem, reopenActionItem } from "@/lib/api";
vi.mock("@/lib/api", () => ({ completeActionItem: vi.fn(), reopenActionItem: vi.fn(), editMemoryItem: vi.fn() }));
const items = [
  {id:"open",task:"Send listings",owner:null,due:null,status:"OPEN",completed_at:null},
  {id:"done",task:"Call lender",owner:null,due:null,status:"COMPLETED",completed_at:"2026-09-24T12:00:00Z"},
];
it("filters task history and performs explicit completion/reopening with error recovery", async () => {
  const user = userEvent.setup();
  const cache = new QueryClient();
  const invalidation = vi.spyOn(cache,"invalidateQueries");
  vi.mocked(completeActionItem).mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce({...items[0],status:"COMPLETED"});
  vi.mocked(reopenActionItem).mockResolvedValue({...items[1],status:"OPEN"});
  render(<QueryClientProvider client={cache}><ConversationTasks memoryId="memory" items={items}/></QueryClientProvider>);
  expect(screen.getByText("1 open · 1 completed")).toBeInTheDocument();
  expect(screen.queryByText("Call lender")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button",{name:"Complete task: Send listings"}));
  expect(await screen.findByRole("alert")).toHaveTextContent("Couldn't update");
  expect(screen.getByText("Send listings")).toBeInTheDocument();
  await user.click(screen.getByRole("button",{name:"Complete task: Send listings"}));
  await waitFor(() => expect(invalidation).toHaveBeenCalledWith({queryKey:["memory"]}));
  expect(completeActionItem).toHaveBeenLastCalledWith("open");
  await user.selectOptions(screen.getByLabelText("Show tasks"),"completed");
  expect(screen.queryByText("Send listings")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button",{name:"Reopen task: Call lender"}));
  await waitFor(() => expect(reopenActionItem).toHaveBeenCalledWith("done"));
  await user.selectOptions(screen.getByLabelText("Show tasks"),"all");
  expect(screen.getByText("Send listings")).toBeInTheDocument();
  expect(screen.getByText("Call lender")).toBeInTheDocument();
});
