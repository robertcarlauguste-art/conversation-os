import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, test, expect } from "vitest";
import { getPilotUsage } from "@/lib/api";
import { PilotUsage } from "./PilotUsage";

vi.mock("@/lib/api", () => ({ getPilotUsage: vi.fn() }));
test("shows exhausted allowance without hiding saved-content access", async () => {
  const values = { recordings: 0, storage_bytes: 0, uploads: 0, audio_seconds: 0, ai: 0, retries: 0 };
  vi.mocked(getPilotUsage).mockResolvedValue({ enabled: true, used: values, remaining: values,
    limits: { ...values, recordings: 30 }, resets_at: "2026-09-28T00:00:00Z" });
  render(<QueryClientProvider client={new QueryClient()}><PilotUsage /><p>Saved notes</p></QueryClientProvider>);
  expect(await screen.findByText("Recordings left today: 0")).toBeInTheDocument();
  expect(screen.getByText("AI requests left today: 0")).toBeInTheDocument();
  expect(screen.getByText("Saved notes")).toBeInTheDocument();
  expect(screen.getByText(/Reading and editing saved notes remain available/)).toBeInTheDocument();
});

