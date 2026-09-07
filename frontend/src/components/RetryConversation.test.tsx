import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import { RetryConversation } from "./RetryConversation";
import { retryConversation } from "@/lib/api";
import type { ConversationDetail, ConversationStatus } from "@/lib/types";

vi.mock("@/lib/api", () => ({ retryConversation: vi.fn() }));

function setup(status: ConversationStatus = "FAILED") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const invalidate = vi.spyOn(client, "invalidateQueries");
  const view = render(<QueryClientProvider client={client}><RetryConversation id="abc" status={status} /></QueryClientProvider>);
  return { client, invalidate, ...view };
}

describe("conversation retry", () => {
  it.each(["UPLOADED", "QUEUED", "PROCESSING", "COMPLETED"] as const)("hides retry for %s", (status) => {
    setup(status);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("disables repeated clicks, seeds queued data and refreshes related queries", async () => {
    let resolve!: (value: ConversationDetail) => void;
    vi.mocked(retryConversation).mockReturnValueOnce(new Promise((done) => { resolve = done; }));
    const { client, invalidate, rerender } = setup();
    const button = screen.getByRole("button", { name: "Retry" });
    fireEvent.click(button);
    fireEvent.click(button);
    await waitFor(() => expect(button).toBeDisabled());
    expect(retryConversation).toHaveBeenCalledTimes(1);
    resolve({ id: "abc", status: "QUEUED" } as ConversationDetail);
    await waitFor(() => expect(client.getQueryData(["conversations", "abc"])).toEqual({ id: "abc", status: "QUEUED" }));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["conversations"] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["transcript", "abc"] });
    rerender(<QueryClientProvider client={client}><RetryConversation id="abc" status="QUEUED" /></QueryClientProvider>);
    expect(await screen.findByRole("status")).toHaveTextContent("Retry queued");
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("shows fixed safe errors and refreshes after uncertain failures", async () => {
    vi.mocked(retryConversation).mockRejectedValueOnce(new Error("private provider body"));
    const { invalidate } = setup();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Refresh the conversation");
    expect(screen.queryByText(/private provider/)).not.toBeInTheDocument();
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["conversations"] });
    expect(screen.getByRole("button", { name: "Retry" })).toBeEnabled();
  });
});
