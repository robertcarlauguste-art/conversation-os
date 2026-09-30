import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { PrepareFollowup } from "./PrepareFollowup";
import { prepareFollowup } from "@/lib/api";
import type { MemoryDetail } from "@/lib/types";

vi.mock("@/lib/api", () => ({ prepareFollowup: vi.fn() }));
const memory = {
  summary: "Private pricing discussion", action_items: [
    { id: "task", task: "Send proposal", owner: "Taylor", due: "Friday", status: "OPEN" },
  ],
} as MemoryDetail;
beforeEach(() => { vi.clearAllMocks(); });

it("requires explicit selection and copies the edited draft without completing tasks", async () => {
  vi.mocked(prepareFollowup).mockResolvedValue({ subject: "Next steps", body: "A proposed message" });
  const copy = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { value: { writeText: copy }, configurable: true });
  render(<PrepareFollowup conversationId="conversation" memory={memory} />);
  expect(screen.getByRole("button", { name: "Draft email or text" })).toHaveAttribute("aria-expanded", "false");
  expect(screen.queryByRole("button", { name: "Prepare draft" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Draft email or text" }));
  expect(screen.getByRole("button", { name: "Draft email or text" })).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByRole("button", { name: "Prepare draft" })).toBeDisabled();
  fireEvent.click(screen.getByRole("checkbox", { name: /Send proposal/ }));
  fireEvent.click(screen.getByRole("button", { name: "Prepare draft" }));
  expect(await screen.findByLabelText("Message")).toHaveValue("A proposed message");
  expect(prepareFollowup).toHaveBeenCalledWith("conversation", { channel: "email", include_summary: false, action_ids: ["task"] });
  fireEvent.change(screen.getByLabelText("Message"), { target: { value: "My corrected message" } });
  fireEvent.click(screen.getByRole("button", { name: "Copy draft" }));
  await waitFor(() => expect(copy).toHaveBeenCalledWith("Subject: Next steps\n\nMy corrected message"));
  expect(memory.action_items[0].status).toBe("OPEN");
});

it("shows allowance errors and keeps selected details for retry", async () => {
  vi.mocked(prepareFollowup).mockRejectedValue(new Error("Today's allowance is used."));
  render(<PrepareFollowup conversationId="conversation" memory={memory} />);
  fireEvent.click(screen.getByRole("button", { name: "Draft email or text" }));
  fireEvent.click(screen.getByRole("checkbox", { name: /Include summary/ }));
  fireEvent.click(screen.getByRole("button", { name: "Prepare draft" }));
  expect(await screen.findByText("Today's allowance is used.")).toBeInTheDocument();
  expect(screen.getByRole("checkbox", { name: /Include summary/ })).toBeChecked();
});

it("offers text format and a manual copy fallback", async () => {
  vi.mocked(prepareFollowup).mockResolvedValue({ subject: "", body: "Next steps" });
  Object.defineProperty(navigator, "clipboard", { value: { writeText: vi.fn().mockRejectedValue(new Error()) }, configurable: true });
  render(<PrepareFollowup conversationId="conversation" memory={memory} />);
  fireEvent.click(screen.getByRole("button", { name: "Draft email or text" }));
  fireEvent.change(screen.getByLabelText("Message format"), { target: { value: "text" } });
  fireEvent.click(screen.getByRole("checkbox", { name: /Include summary/ }));
  fireEvent.click(screen.getByRole("button", { name: "Prepare draft" }));
  await screen.findByLabelText("Message");
  expect(screen.queryByLabelText("Subject")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Copy draft" }));
  expect(await screen.findByText(/copy it manually/)).toBeInTheDocument();
});
