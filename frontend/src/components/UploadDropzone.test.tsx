import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { UploadDropzone } from "./UploadDropzone";
import { listClients, uploadConversation } from "@/lib/api";
vi.mock("@/lib/api", () => ({ listClients: vi.fn(), uploadConversation: vi.fn(), createClient: vi.fn(), ApiError: class extends Error {} }));
vi.mock("./Toast", () => ({ useToast: () => ({notify: vi.fn()}) }));
it.each(["existing", "later"])("sends the explicit %s assignment with uploaded audio", async mode => {
  vi.mocked(listClients).mockResolvedValue([{id:"vale",full_name:"Morgan Vale"}] as never);
  vi.mocked(uploadConversation).mockResolvedValue({id:"recording",status:"QUEUED"});
  const user = userEvent.setup();
  const {container} = render(<QueryClientProvider client={new QueryClient()}><UploadDropzone /></QueryClientProvider>);
  expect(screen.queryByRole("button",{name:"Start recording"})).not.toBeInTheDocument();
  if (mode === "existing") {
    await screen.findByRole("option",{name:"Morgan Vale"});
    await user.selectOptions(screen.getByLabelText("Recording client"),"vale");
  } else await user.selectOptions(screen.getByLabelText("Client choice"),"later");
  await user.click(screen.getByRole("button",{name:"Continue to record or upload"}));
  expect(screen.getByRole("button",{name:"Start recording"})).toBeEnabled();
  const file = new File(["audio"],"test.wav",{type:"audio/wav"});
  await user.upload(container.querySelector('input[type="file"]')!,file);
  await waitFor(() => expect(uploadConversation).toHaveBeenLastCalledWith(file,expect.any(Function),mode === "existing" ? "vale" : null));
});
