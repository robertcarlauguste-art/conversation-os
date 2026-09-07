import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ConversationDetail } from "@/lib/types";
import { ProcessingDetails } from "./ProcessingDetails";

const conversation: ConversationDetail = {
  id: "one",
  title: null,
  filename: "test.wav",
  mime_type: "audio/wav",
  file_size: 1,
  duration_seconds: null,
  status: "FAILED",
  source: "UPLOAD",
  client_id: null,
  created_at: "2026-09-07T12:00:00Z",
  updated_at: "2026-09-07T12:05:00Z",
  processing_attempts: 3,
  processing_started_at: "2026-09-07T12:01:00Z",
  processing_completed_at: "2026-09-07T12:05:00Z",
  processing_error:
    "Processing failed. Check provider configuration and worker availability.",
  is_stale: false,
  stale_threshold_seconds: 900,
};

describe("Processing details", () => {
  it("shows attempt timing and safe error with a failed terminal label", () => {
    render(<ProcessingDetails conversation={conversation} />);
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("Failed")).toBeInTheDocument();
    expect(
      screen.getByText(/Latest error: Processing failed/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        new Date(conversation.processing_started_at!).toLocaleString(),
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
  it("shows the backend stale warning and missing legacy timing", () => {
    render(
      <ProcessingDetails
        conversation={{
          ...conversation,
          status: "PROCESSING",
          is_stale: true,
          processing_started_at: null,
          processing_completed_at: null,
          processing_error: null,
        }}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("15 minutes");
    expect(screen.getByRole("status")).toHaveTextContent(
      "does not confirm abandonment",
    );
    expect(screen.getAllByText("Not recorded")).toHaveLength(2);
    expect(screen.queryByText(/Latest error/)).not.toBeInTheDocument();
  });
  it("labels successful terminal timing completed", () => {
    render(
      <ProcessingDetails
        conversation={{
          ...conversation,
          status: "COMPLETED",
          processing_error: null,
        }}
      />,
    );
    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(screen.queryByText("Failed")).not.toBeInTheDocument();
  });
});
