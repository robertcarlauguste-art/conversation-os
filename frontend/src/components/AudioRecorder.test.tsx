import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { AudioRecorder } from "./AudioRecorder";
import { LanguageProvider, LanguageSelector } from "./LanguageProvider";

const stopTrack = vi.fn();
let active: FakeRecorder;
class FakeRecorder {
  static isTypeSupported = () => true;
  state = "inactive";
  ondataavailable?: (event: { data: Blob }) => void;
  onstop?: () => void;
  constructor() { active = this; }
  start() { this.state = "recording"; }
  stop() { this.state = "inactive"; this.ondataavailable?.({ data: new Blob(["audio"]) }); this.onstop?.(); }
}
beforeEach(() => {
  vi.stubGlobal("MediaRecorder", FakeRecorder);
  Object.defineProperty(navigator, "mediaDevices", { configurable: true, value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop: stopTrack }] }) } });
  URL.createObjectURL = vi.fn(() => "blob:preview");
  URL.revokeObjectURL = vi.fn();
});
afterEach(() => vi.unstubAllGlobals());

it("records locally, previews, and retains audio when submission fails", async () => {
  const submit = vi.fn().mockResolvedValueOnce(false).mockResolvedValueOnce(true);
  render(<AudioRecorder onSubmit={submit} disabled={false} />);
  fireEvent.click(screen.getByText("Start recording"));
  fireEvent.click(await screen.findByText("Stop and review"));
  expect(stopTrack).toHaveBeenCalled();
  expect(submit).not.toHaveBeenCalled();
  expect(screen.getByLabelText("Recording preview")).toBeInTheDocument();
  fireEvent.click(screen.getByText("Submit recording"));
  await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
  expect(submit.mock.calls[0][0].type).toBe("audio/webm");
  expect(screen.getByText("Discard recording")).toBeInTheDocument();
  fireEvent.click(screen.getByText("Submit recording"));
  expect(await screen.findByText("Start recording")).toBeInTheDocument();
});

it("explains permission denial without uploading", async () => {
  vi.mocked(navigator.mediaDevices.getUserMedia).mockRejectedValue(new Error("denied"));
  render(<AudioRecorder onSubmit={vi.fn()} disabled={false} />);
  fireEvent.click(screen.getByText("Start recording"));
  expect(await screen.findByRole("alert")).toHaveTextContent("Allow microphone access");
});

it("releases the microphone when leaving the page", async () => {
  const view = render(<AudioRecorder onSubmit={vi.fn()} disabled={false} />);
  fireEvent.click(screen.getByText("Start recording"));
  await screen.findByText("Stop and review");
  view.unmount();
  expect(active.state).toBe("inactive");
  expect(stopTrack).toHaveBeenCalled();
});

it("releases a late permission response after leaving", async () => {
  let resolve!: (stream: MediaStream) => void;
  vi.mocked(navigator.mediaDevices.getUserMedia).mockReturnValue(new Promise(r => { resolve = r; }));
  const view = render(<AudioRecorder onSubmit={vi.fn()} disabled={false} />);
  fireEvent.click(screen.getByText("Start recording"));
  view.unmount();
  await act(async () => resolve({ getTracks: () => [{ stop: stopTrack }] } as unknown as MediaStream));
  expect(stopTrack).toHaveBeenCalled();
});

it("stops automatically at the pilot duration limit", async () => {
  vi.useFakeTimers();
  try {
    render(<AudioRecorder onSubmit={vi.fn()} disabled={false} />);
    await act(async () => { fireEvent.click(screen.getByText("Start recording")); });
    act(() => { vi.advanceTimersByTime(180_000); });
    expect(screen.getByText("Submit recording")).toBeInTheDocument();
    expect(active.state).toBe("inactive");
  } finally { vi.useRealTimers(); }
});

it("offers upload guidance when recording is unsupported", () => {
  vi.stubGlobal("MediaRecorder", undefined);
  render(<AudioRecorder onSubmit={vi.fn()} disabled={false} />);
  fireEvent.click(screen.getByText("Start recording"));
  expect(screen.getByRole("alert")).toHaveTextContent("upload an audio file");
});

it("keeps recording and preview audio when the language changes", async () => {
  localStorage.clear();
  const submit = vi.fn().mockResolvedValue(true);
  render(<LanguageProvider><LanguageSelector /><AudioRecorder onSubmit={submit} disabled={false} /></LanguageProvider>);
  fireEvent.click(screen.getByText("Start recording"));
  await screen.findByText("Stop and review");
  const original = active;
  fireEvent.change(screen.getByLabelText("Language / Lang"), { target: { value: "ht" } });
  expect(active).toBe(original);
  expect(active.state).toBe("recording");
  fireEvent.click(screen.getByText("Kanpe epi verifye"));
  const preview = screen.getByLabelText("Koute anrejistreman an").getAttribute("src");
  fireEvent.change(screen.getByLabelText("Language / Lang"), { target: { value: "es" } });
  expect(screen.getByLabelText("Escuchar la grabación")).toHaveAttribute("src", preview);
  expect(submit).not.toHaveBeenCalled();
  localStorage.clear();
});
