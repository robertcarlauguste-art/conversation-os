import { act, render, screen, waitFor } from "@testing-library/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import { getAccessToken } from "@/lib/auth-token";
import { Providers } from "./providers";

const identity = vi.hoisted(() => ({
  isLoaded: true,
  userId: "alpha" as string | null,
  sessionId: "alpha-session" as string | null,
  getToken: vi.fn(async () => "alpha" as string | null),
}));
vi.mock("@clerk/nextjs", () => ({ useAuth: () => identity }));

describe("tenant browser cache", () => {
  it("isolates account switches, late responses, sign-out and session changes", async () => {
    let resolveOld: (value: string) => void = () => {};
    const oldResponse = new Promise<string>((resolve) => { resolveOld = resolve; });
    const clients: ReturnType<typeof useQueryClient>[] = [];
    const tokens: (string | null)[] = [];
    function Probe() {
      const client = useQueryClient();
      if (!clients.includes(client)) clients.push(client);
      const query = useQuery({
        queryKey: ["conversations"],
        queryFn: async () => {
          const token = await getAccessToken();
          tokens.push(token);
          return token === "alpha" ? oldResponse : `data:${token}`;
        },
      });
      return <div>{query.data ?? "loading"}</div>;
    }
    const view = render(<Providers authEnabled><Probe /></Providers>);
    await waitFor(() => expect(tokens).toEqual(["alpha"]));
    act(() => { clients[0].setQueryData<string>(["conversations"], "private_alpha"); });
    expect(await screen.findByText("private_alpha")).toBeInTheDocument();
    identity.userId = "beta";
    identity.sessionId = "beta-session";
    identity.getToken = vi.fn(async () => "beta");
    view.rerender(<Providers authEnabled><Probe /></Providers>);
    expect(screen.queryByText("private_alpha")).not.toBeInTheDocument();
    expect(await screen.findByText("data:beta")).toBeInTheDocument();
    await act(async () => resolveOld("late_private_alpha"));
    expect(screen.queryByText("late_private_alpha")).not.toBeInTheDocument();
    expect(clients[1].getQueryData(["conversations"])).toBe("data:beta");
    identity.sessionId = "beta-session-2";
    view.rerender(<Providers authEnabled><Probe /></Providers>);
    await waitFor(() => expect(clients).toHaveLength(3));
    identity.userId = null;
    identity.sessionId = null;
    identity.getToken = vi.fn(async () => null);
    view.rerender(<Providers authEnabled><Probe /></Providers>);
    expect(screen.queryByText("data:beta")).not.toBeInTheDocument();
    expect(await screen.findByText("data:null")).toBeInTheDocument();
    expect(clients).toHaveLength(4);
    view.unmount();
    expect(await getAccessToken()).toBeNull();
  });
});
