import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { ClientConversations } from "./ClientConversations";
const item = {id:"one", title:"Jordan — Home buying", filename:"note.webm", status:"COMPLETED", created_at:"2026-09-25T10:00:00Z", summary_preview:"Budget increased to $375,000."};
it("distinguishes conversations using summaries and dates with direct links", () => {
  render(<ClientConversations conversations={[item, {...item,id:"two",created_at:"2026-09-24T10:00:00Z",summary_preview:"Listings sent; lender call outstanding."}]} loading={false} error={false} onRetry={vi.fn()} />);
  expect(screen.getByText("Budget increased to $375,000.")).toBeInTheDocument();
  expect(screen.getByText("Listings sent; lender call outstanding.")).toBeInTheDocument();
  expect(screen.getAllByRole("link").map(link => link.getAttribute("href"))).toEqual(["/conversations/one","/conversations/two"]);
  expect(document.querySelectorAll("time")).toHaveLength(2);
});
it("uses summary for an old generic title and handles missing summaries", () => {
  render(<ClientConversations conversations={[{...item,title:"Conversation"},{...item,id:"two",title:null,summary_preview:null}]} loading={false} error={false} onRetry={vi.fn()} />);
  expect(screen.getByRole("heading",{name:item.summary_preview})).toBeInTheDocument();
  expect(screen.getByText(/No summary available/)).toBeInTheDocument();
});
it("shows a recoverable loading error rather than a false empty list", () => {
  const retry=vi.fn();
  render(<ClientConversations conversations={[]} loading={false} error onRetry={retry} />);
  expect(screen.getByRole("alert")).toHaveTextContent("Couldn't load conversations");
  expect(screen.queryByText("No linked conversations yet.")).not.toBeInTheDocument();
  fireEvent.click(screen.getByText("Try again"));
  expect(retry).toHaveBeenCalledOnce();
});
