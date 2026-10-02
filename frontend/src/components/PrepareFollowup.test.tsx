import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { PrepareFollowup } from "./PrepareFollowup";
import { getSavedFollowup, prepareFollowup, saveFollowup } from "@/lib/api";
import type { MemoryDetail } from "@/lib/types";

vi.mock("@/lib/api", () => ({ prepareFollowup: vi.fn(), getSavedFollowup: vi.fn(), saveFollowup: vi.fn() }));
const memory = {
  summary: "Private pricing discussion", action_items: [
    { id: "task", task: "Send proposal", owner: "Taylor", due: "Friday", status: "OPEN" },
  ],
} as MemoryDetail;
beforeEach(() => { vi.clearAllMocks(); vi.mocked(getSavedFollowup).mockResolvedValue(null); });

it("defaults to no recipient and sends only an explicitly chosen confirmed person ID", async () => {
  vi.mocked(prepareFollowup).mockResolvedValue({ subject: "Hello", body: "Follow-up" });
  render(<PrepareFollowup conversationId="conversation" memory={{ ...memory, people: [
    { id: "confirmed", name: "Morgan Vail", confirmed_name: "Morgan Vale", role: null },
    { id: "unconfirmed", name: "Other person", role: null },
  ] }} />);
  fireEvent.click(screen.getByRole("button", { name: "Draft email or text" }));
  const recipient = await screen.findByLabelText("Who is this message for?");
  expect(recipient).toHaveValue("");
  expect(screen.queryByRole("option", { name: "Other person" })).not.toBeInTheDocument();
  fireEvent.change(recipient, { target: { value: "confirmed" } });
  fireEvent.click(screen.getByRole("checkbox", { name: /Send proposal/ }));
  fireEvent.click(screen.getByRole("button", { name: "Prepare draft" }));
  await screen.findByLabelText("Message");
  expect(prepareFollowup).toHaveBeenCalledWith("conversation", {
    channel: "email", include_summary: false, action_ids: ["task"], recipient_person_id: "confirmed",
  });
});

it("reopens saved content and saves edits with its version without generating AI", async () => {
  const saved = { subject: "Saved subject", body: "Saved message", channel: "email" as const, version: 2, updated_at: "2026-10-01T12:00:00Z" };
  vi.mocked(getSavedFollowup).mockResolvedValue(saved);
  vi.mocked(saveFollowup).mockResolvedValue({ ...saved, body: "Edited message", version: 3 });
  render(<PrepareFollowup conversationId="conversation" memory={memory} />);
  fireEvent.click(screen.getByRole("button", { name: "Draft email or text" }));
  expect(await screen.findByLabelText("Message")).toHaveValue("Saved message");
  fireEvent.change(screen.getByLabelText("Message"), { target: { value: "Edited message" } });
  fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
  await screen.findByText("Draft saved. You can return to this conversation later.");
  expect(saveFollowup).toHaveBeenCalledWith("conversation", "email", { subject: "Saved subject", body: "Edited message" }, 2);
  expect(prepareFollowup).not.toHaveBeenCalled();
  expect(screen.queryByText("Unsaved changes")).not.toBeInTheDocument();
});

it("keeps unsaved edits on a save conflict", async () => {
  vi.mocked(getSavedFollowup).mockResolvedValue({ subject: "", body: "Existing", channel: "email", version: 1, updated_at: "2026-10-01T12:00:00Z" });
  vi.mocked(saveFollowup).mockRejectedValue(new Error("This draft changed in another tab."));
  render(<PrepareFollowup conversationId="conversation" memory={memory} />);
  fireEvent.click(screen.getByRole("button", { name: "Draft email or text" }));
  fireEvent.change(await screen.findByLabelText("Message"), { target: { value: "Keep my edit" } });
  fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
  await screen.findByText("This draft changed in another tab.");
  expect(screen.getByLabelText("Message")).toHaveValue("Keep my edit");
  expect(screen.getByText("Unsaved changes")).toBeInTheDocument();
});

it("requires explicit selection and copies the edited draft without completing tasks", async () => {
  vi.mocked(prepareFollowup).mockResolvedValue({ subject: "Next steps", body: "A proposed message" });
  const copy = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { value: { writeText: copy }, configurable: true });
  render(<PrepareFollowup conversationId="conversation" memory={memory} />);
  expect(screen.getByRole("button", { name: "Draft email or text" })).toHaveAttribute("aria-expanded", "false");
  expect(screen.queryByRole("button", { name: "Prepare draft" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Draft email or text" }));
  expect(screen.getByRole("button", { name: "Draft email or text" })).toHaveAttribute("aria-expanded", "true");
  expect(await screen.findByRole("button", { name: "Prepare draft" })).toBeDisabled();
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
  fireEvent.click(await screen.findByRole("checkbox", { name: /Include summary/ }));
  fireEvent.click(screen.getByRole("button", { name: "Prepare draft" }));
  expect(await screen.findByText("Today's allowance is used.")).toBeInTheDocument();
  expect(screen.getByRole("checkbox", { name: /Include summary/ })).toBeChecked();
});

it("offers text format and a manual copy fallback", async () => {
  vi.mocked(prepareFollowup).mockResolvedValue({ subject: "", body: "Next steps" });
  Object.defineProperty(navigator, "clipboard", { value: { writeText: vi.fn().mockRejectedValue(new Error()) }, configurable: true });
  render(<PrepareFollowup conversationId="conversation" memory={memory} />);
  fireEvent.click(screen.getByRole("button", { name: "Draft email or text" }));
  await screen.findByRole("checkbox", { name: /Include summary/ });
  fireEvent.change(screen.getByLabelText("Message format"), { target: { value: "text" } });
  fireEvent.click(await screen.findByRole("checkbox", { name: /Include summary/ }));
  fireEvent.click(screen.getByRole("button", { name: "Prepare draft" }));
  await screen.findByLabelText("Message");
  expect(screen.queryByLabelText("Subject")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Copy draft" }));
  expect(await screen.findByText(/copy it manually/)).toBeInTheDocument();
});
