import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expect, it, vi } from "vitest";
import { CompareClients } from "./CompareClients";
const get = vi.hoisted(() => vi.fn().mockResolvedValue([]));
vi.mock("@/lib/api", () => ({ getClientConversations: get }));
it("loads histories only after two distinct records are selected", async () => {
  const clients = [
    { id: "a", full_name: "Morgan Vale", email: null, phone: null, created_at: "2026-10-04" },
    { id: "b", full_name: "Morgan Vail", email: null, phone: null, created_at: "2026-10-04" },
  ];
  render(<QueryClientProvider client={new QueryClient()}><CompareClients clients={clients} /></QueryClientProvider>);
  fireEvent.click(screen.getByText("Different spellings? Compare client records"));
  fireEvent.change(screen.getByLabelText("First client"), { target: { value: "a" } });
  expect(get).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("Second client"), { target: { value: "b" } });
  await waitFor(() => expect(screen.getAllByText("No linked conversations yet.")).toHaveLength(2));
  expect(get).toHaveBeenCalledWith("a", "");
  expect(get).toHaveBeenCalledWith("b", "");
  expect(screen.getByRole("link", { name: "Morgan Vale" })).toHaveAttribute("href", "/clients/a");
  expect(screen.getByRole("link", { name: "Morgan Vail" })).toHaveAttribute("href", "/clients/b");
});
