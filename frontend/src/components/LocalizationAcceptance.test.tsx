import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { LanguageProvider, LanguageSelector, useLanguage } from "./LanguageProvider";
import { StatusBadge } from "./StatusBadge";
import { ClientConversations } from "./ClientConversations";
import { formatDate, formatTimestamp, conversationTitle } from "@/lib/format";
import { translate, type Language } from "@/lib/onboarding-translations";

afterEach(() => { localStorage.clear(); vi.restoreAllMocks(); });

it("switches all five status badges without changing saved content or making requests", () => {
  const request = vi.spyOn(globalThis, "fetch");
  const record = Object.freeze({ id: "fixture", filename: "fixture.webm", title: "Mari — Saved title", summary_preview: "Saved English summary: $1,250", status: "COMPLETED", created_at: "2026-10-11T06:02:00Z" });
  render(<LanguageProvider><LanguageSelector />
    {(["UPLOADED", "QUEUED", "PROCESSING", "COMPLETED", "FAILED"] as const).map(status => <StatusBadge key={status} status={status} />)}
    <ClientConversations conversations={[record]} loading={false} error={false} onRetry={() => {}} />
  </LanguageProvider>);
  for (const language of ["en", "ht", "fr", "es"] as const) {
    fireEvent.change(screen.getByLabelText("Language / Lang"), { target: { value: language } });
    for (const label of ["Received", "Waiting to start", "Preparing your notes", "Ready to review", "Needs attention"]) {
      expect(screen.getAllByText(translate(language, label)).length).toBeGreaterThan(0);
    }
    expect(screen.getByText(record.title)).toBeInTheDocument();
    expect(screen.getByText(record.summary_preview)).toBeInTheDocument();
    expect(conversationTitle(record, language)).toBe(record.title);
  }
  expect(request).not.toHaveBeenCalled();
});

it("switches application dates and section-specific empty wording", () => {
  function Example() {
    const { language, t } = useLanguage();
    return <><time>{formatDate("2026-10-11T06:02:00Z", language)}</time><p>{t("No decisions identified.")}</p><p>{t("No people identified.")}</p><p>{t("Not recorded")}</p></>;
  }
  render(<LanguageProvider><LanguageSelector /><Example /></LanguageProvider>);
  fireEvent.change(screen.getByLabelText("Language / Lang"), { target: { value: "es" } });
  expect(screen.getByText("No se identificaron decisiones.")).toBeInTheDocument();
  expect(screen.getByText("No se identificaron personas.")).toBeInTheDocument();
  expect(screen.getByText("Sin registrar")).toBeInTheDocument();
  expect(screen.getByText(formatDate("2026-10-11T06:02:00Z", "es"))).toBeInTheDocument();
});

it.each(["en", "ht", "fr", "es"] as Language[])("preserves instants across DST boundaries in %s", language => {
  const options = { timeZone: "America/New_York", hour: "2-digit", minute: "2-digit", hour12: false } as const;
  expect(formatTimestamp("2026-03-08T06:59:00Z", language, options)).toContain("01:59");
  expect(formatTimestamp("2026-03-08T07:01:00Z", language, options)).toContain("03:01");
  expect(formatTimestamp("2026-11-01T05:30:00Z", language, options)).toContain("01:30");
  expect(formatTimestamp("2026-11-01T06:30:00Z", language, options)).toContain("01:30");
});

it("uses a predictable numeric Creole fallback and leaves the default timezone alone", () => {
  expect(formatTimestamp("2026-10-11T06:02:00Z", "ht", { timeZone: "UTC" })).toBe("11/10/2026, 06:02");
  const format = vi.spyOn(Date.prototype, "toLocaleString");
  formatDate("2026-10-11T06:02:00Z", "fr");
  expect(format.mock.calls[0][0]).toBe("fr");
  expect(format.mock.calls[0][1]).not.toHaveProperty("timeZone");
});

