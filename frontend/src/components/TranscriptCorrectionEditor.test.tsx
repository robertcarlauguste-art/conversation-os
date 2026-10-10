import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expect, it, vi } from "vitest";
import { TranscriptCorrectionEditor } from "./TranscriptCorrectionEditor";
import * as api from "@/lib/api";
vi.mock("@/lib/api",()=>({getTranscriptCorrection:vi.fn(),saveTranscriptCorrection:vi.fn(),previewTranscriptCorrection:vi.fn()}));
it("preserves edits on save conflict and does not generate notes automatically",async()=>{
 vi.mocked(api.getTranscriptCorrection).mockResolvedValue(null);
 vi.mocked(api.saveTranscriptCorrection).mockRejectedValue(new Error("Changed in another tab"));
 render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><TranscriptCorrectionEditor conversationId="id" original="ma po et"/></QueryClientProvider>);
 fireEvent.click(await screen.findByRole("button",{name:"Correct transcript"}));
 fireEvent.change(screen.getByLabelText("Corrected transcript"),{target:{value:"m'ap voye"}});
 fireEvent.click(screen.getByRole("button",{name:"Save correction"}));
 expect(await screen.findByRole("alert")).toHaveTextContent("Changed in another tab");
 expect(screen.getByLabelText("Corrected transcript")).toHaveValue("m'ap voye");
 expect(api.previewTranscriptCorrection).not.toHaveBeenCalled();
 await waitFor(()=>expect(api.saveTranscriptCorrection).toHaveBeenCalledWith("id","m'ap voye",0));
});
