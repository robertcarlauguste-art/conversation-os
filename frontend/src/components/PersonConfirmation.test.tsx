import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, expect, it, vi } from "vitest";
import { confirmPerson, listClients } from "@/lib/api";
import { PersonConfirmation } from "./PersonConfirmation";

vi.mock("@/lib/api", () => ({ confirmPerson: vi.fn(), listClients: vi.fn() }));
beforeEach(() => { vi.resetAllMocks(); vi.mocked(listClients).mockResolvedValue([{ id: "client", full_name: "Morgan Vale" }] as never); });
function show(confirmed_name: string | null = null) {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><ul><PersonConfirmation memoryId="memory" person={{ id: "person", name: "Morgan Vail", role: null, confirmed_name }} /></ul></QueryClientProvider>);
}
it("requires explicit client selection and keeps it after save failure", async () => {
  vi.mocked(confirmPerson).mockRejectedValueOnce(new Error("offline")).mockResolvedValue(undefined);
  show();
  fireEvent.click(screen.getByRole("button", { name: "Confirm this person" }));
  await screen.findByRole("option", { name: "Morgan Vale" });
  expect(screen.getByRole("button", { name: "Save confirmation" })).toBeDisabled();
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "client" } });
  fireEvent.click(screen.getByRole("button", { name: "Save confirmation" }));
  await screen.findByRole("alert");
  expect(screen.getByRole("combobox")).toHaveValue("client");
  fireEvent.click(screen.getByRole("button", { name: "Save confirmation" }));
  await waitFor(() => expect(screen.queryByRole("combobox")).not.toBeInTheDocument());
  expect(confirmPerson).toHaveBeenLastCalledWith("memory", "person", "client");
});
it("shows the original name and allows removing confirmation", async () => {
  vi.mocked(confirmPerson).mockResolvedValue(undefined);
  show("Morgan Vale");
  expect(screen.getByText(/Originally extracted: Morgan Vail/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Change confirmation" }));
  fireEvent.click(screen.getByRole("button", { name: "Remove confirmation" }));
  await waitFor(() => expect(confirmPerson).toHaveBeenCalledWith("memory", "person", null));
});
