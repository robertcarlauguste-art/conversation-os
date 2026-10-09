import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LanguageProvider, LanguageSelector } from "./LanguageProvider";
import { ConversationTasks } from "./ConversationTasks";
import { workflowCopy } from "@/lib/workflow-translations";
import { copy, translate } from "@/lib/onboarding-translations";

afterEach(() => localStorage.clear());
it("keeps task edits intact when switching among pilot languages", () => {
  render(<QueryClientProvider client={new QueryClient()}><LanguageProvider><LanguageSelector /><ConversationTasks memoryId="memory" items={[{id:"task", task:"Send Mari $1,250 estimate", owner:"Mari", due:"Friday", status:"OPEN", original:null, completed_at:null}]} /></LanguageProvider></QueryClientProvider>);
  fireEvent.click(screen.getByRole("button", {name:"Edit task: Send Mari $1,250 estimate"}));
  fireEvent.change(screen.getByLabelText("Task"), {target:{value:"My own corrected wording"}});
  for (const language of ["ht", "fr", "es"] as const) {
    fireEvent.change(screen.getByLabelText("Language / Lang"), {target:{value:language}});
    expect(screen.getByLabelText(translate(language,"Task"))).toHaveValue("My own corrected wording");
    expect(screen.getByLabelText(translate(language,"Owner (optional)"))).toHaveValue("Mari");
    expect(screen.getByRole("button",{name:translate(language,"Save changes")})).toBeInTheDocument();
  }
});
it("supplies complete workflow translations with matching placeholders", () => {
  const all=[...copy,...workflowCopy];
  expect(new Set(all.map(row=>row[0])).size).toBe(all.length);
  for(const row of workflowCopy) for(const value of row) {
    expect(value.trim()).not.toBe("");
    expect((value.match(/\{\w+\}/g)??[]).sort()).toEqual((row[0].match(/\{\w+\}/g)??[]).sort());
  }
});

