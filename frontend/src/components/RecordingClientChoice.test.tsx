import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { RecordingClientChoice } from "./RecordingClientChoice";
import { createClient, listClients } from "@/lib/api";
vi.mock("@/lib/api", () => ({ listClients: vi.fn(), createClient: vi.fn() }));
function setup() {
  vi.mocked(listClients).mockResolvedValue([{ id: "vale", full_name: "Morgan Vale", email: null }] as never);
  const confirm = vi.fn();
  render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><RecordingClientChoice onConfirm={confirm} /></QueryClientProvider>);
  return confirm;
}
it("requires a choice and confirms an existing identity by ID", async () => {
  const confirm = setup(); const user = userEvent.setup();
  expect(screen.getByRole("button", {name:"Continue to record or upload"})).toBeDisabled();
  await screen.findByRole("option", {name:"Morgan Vale"});
  await user.selectOptions(screen.getByLabelText("Recording client"), "vale");
  await user.click(screen.getByRole("button", {name:"Continue to record or upload"}));
  expect(confirm).toHaveBeenCalledWith({id:"vale", name:"Morgan Vale"});
});
it("supports explicit assign later", async () => {
  const confirm = setup(); const user = userEvent.setup();
  await user.selectOptions(screen.getByLabelText("Client choice"), "later");
  await user.click(screen.getByRole("button", {name:"Continue to record or upload"}));
  expect(confirm).toHaveBeenCalledWith({id:null, name:"Assign later"});
});
it("retains a new name on failure and confirms only after successful creation", async () => {
  const confirm = setup(); const user = userEvent.setup();
  vi.mocked(createClient).mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce({id:"new",full_name:"Morgan Lane"} as never);
  await user.selectOptions(screen.getByLabelText("Client choice"), "new");
  await user.type(screen.getByLabelText("New client name"), "Morgan Lane");
  await user.click(screen.getByRole("button", {name:"Continue to record or upload"}));
  expect(await screen.findByRole("alert")).toHaveTextContent("Couldn't save");
  expect(confirm).not.toHaveBeenCalled();
  expect(screen.getByLabelText("New client name")).toHaveValue("Morgan Lane");
  await user.click(screen.getByRole("button", {name:"Continue to record or upload"}));
  expect(confirm).toHaveBeenCalledWith({id:"new",name:"Morgan Lane"});
});
