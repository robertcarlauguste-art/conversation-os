import { describe, expect, it, vi } from "vitest";
import { authenticatedFetch } from "./auth-token";
import { retryConversation } from "./api";

vi.mock("./auth-token", () => ({ authenticatedFetch: vi.fn(), getAccessToken: vi.fn() }));

describe("retry API", () => {
  it("uses authenticated POST and returns queued details", async () => {
    vi.mocked(authenticatedFetch).mockResolvedValueOnce(new Response(JSON.stringify({ data: { id: "abc", status: "QUEUED" } })));
    expect(await retryConversation("abc")).toEqual({ id: "abc", status: "QUEUED" });
    expect(authenticatedFetch).toHaveBeenCalledWith(expect.stringContaining("/conversations/abc/retry"), { method: "POST" });
  });
  it.each([401, 404, 409, 503])("contains arbitrary server errors (%s)", async (status) => {
    vi.mocked(authenticatedFetch).mockResolvedValueOnce(new Response("private provider body", { status }));
    await expect(retryConversation("abc")).rejects.toThrow("Couldn't queue the retry. Refresh the conversation before trying again.");
  });
  it("contains network failures", async () => {
    vi.mocked(authenticatedFetch).mockRejectedValueOnce(new Error("private network detail"));
    await expect(retryConversation("abc")).rejects.toThrow("Couldn't queue the retry. Refresh the conversation before trying again.");
  });
});
