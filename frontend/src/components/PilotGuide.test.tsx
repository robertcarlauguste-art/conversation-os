import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { LanguageProvider, LanguageSelector } from "./LanguageProvider";
import { PilotGuide, PilotHelpLink } from "./PilotGuide";
import { helpCopy } from "@/lib/help-translations";
import { translate } from "@/lib/onboarding-translations";
afterEach(() => localStorage.clear());
it("translates every help question and answer without changing numeric limits", () => {
  for(const row of helpCopy) for(const value of row) {
    expect(value.trim()).not.toBe("");
    expect(value.match(/\d+/g)??[]).toEqual(row[0].match(/\d+/g)??[]);
  }
  render(<LanguageProvider><LanguageSelector/><PilotHelpLink/><PilotGuide/></LanguageProvider>);
  for(const language of ["ht","fr","es"] as const) {
    fireEvent.change(screen.getByLabelText("Language / Lang"),{target:{value:language}});
    expect(screen.getByRole("link",{name:translate(language,"Help: getting started, privacy & limits")})).toHaveAttribute("href","#pilot-help");
    for(const row of helpCopy.slice(0,-2)) expect(screen.getByText(translate(language,row[0]))).toBeInTheDocument();
    expect(screen.getByRole("region",{name:translate(language,"Pilot help")})).toHaveAttribute("lang",language);
  }
});
