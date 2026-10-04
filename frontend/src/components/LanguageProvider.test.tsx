import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { useState } from "react";
import { LanguageProvider, LanguageSelector, useLanguage } from "./LanguageProvider";
import { Welcome } from "./Welcome";
import { copy, translate } from "@/lib/onboarding-translations";

vi.mock("@clerk/nextjs", () => ({ SignInButton: ({ children }: { children: React.ReactNode }) => children, SignUpButton: ({ children }: { children: React.ReactNode }) => children }));
afterEach(() => { localStorage.clear(); vi.restoreAllMocks(); });

it("persists an explicit choice across visits and translates the welcome", () => {
  const view = render(<LanguageProvider><Welcome /></LanguageProvider>);
  fireEvent.change(screen.getByLabelText("Language / Lang"), { target: { value: "ht" } });
  expect(screen.getByRole("button", { name: "Eseye premye anrejistreman ou" })).toBeInTheDocument();
  expect(screen.getByRole("main")).toHaveAttribute("lang", "ht");
  view.unmount();
  render(<LanguageProvider><Welcome /></LanguageProvider>);
  expect(screen.getByLabelText("Language / Lang")).toHaveValue("ht");
});

it("changes interface language without remounting or changing user-entered content", () => {
  function Form() {
    const [name, setName] = useState("");
    const { t } = useLanguage();
    return <input aria-label={t("Client name")} value={name} onChange={e => setName(e.target.value)} />;
  }
  render(<LanguageProvider><LanguageSelector /><Form /></LanguageProvider>);
  fireEvent.change(screen.getByLabelText("Client name"), { target: { value: "Mari {name}" } });
  fireEvent.change(screen.getByLabelText("Language / Lang"), { target: { value: "fr" } });
  expect(screen.getByLabelText("Nom du client")).toHaveValue("Mari {name}");
  expect(translate("fr", "This recording will be saved to {name}.", { name: "Mari {name}" })).toBe("Cet enregistrement sera associé à Mari {name}.");
});

it("ignores invalid saved values and works when storage is blocked", () => {
  localStorage.setItem("conversationos-interface-language", "__proto__");
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
  render(<LanguageProvider><Welcome /></LanguageProvider>);
  expect(screen.getByLabelText("Language / Lang")).toHaveValue("en");
  fireEvent.change(screen.getByLabelText("Language / Lang"), { target: { value: "es" } });
  expect(screen.getByRole("button", { name: "Prueba tu primera grabación" })).toBeInTheDocument();
});

it("includes all four translations and preserves interpolation fields", () => {
  expect(new Set(copy.map(row => row[0])).size).toBe(copy.length);
  for (const row of copy) {
    for (const value of row) {
      expect(value.trim()).not.toBe("");
      expect(value.match(/\{\w+\}/g) ?? []).toEqual(row[0].match(/\{\w+\}/g) ?? []);
    }
  }
});
