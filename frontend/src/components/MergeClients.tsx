"use client";
import { useLanguage } from "@/components/LanguageProvider";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { previewClientMerge, confirmClientMerge, type ClientMergePreview } from "@/lib/api";
export function MergeClients({ source, target, onMerged }: { source: string; target: string; onMerged: () => void }) {
  const { t } = useLanguage();
  const [preview, setPreview] = useState<ClientMergePreview | null>(null);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const cache = useQueryClient();
  async function review() {
    setBusy(true); setError("");
    try { setPreview(await previewClientMerge(source, target)); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not prepare the merge."); }
    finally { setBusy(false); }
  }
  async function merge() {
    if (!preview || busy || name !== preview.target.full_name) return;
    setBusy(true); setError("");
    try {
      await confirmClientMerge(source, target, preview.token, name);
      await cache.invalidateQueries();
      onMerged();
    } catch (e) { setError(e instanceof Error ? e.message : "Could not merge records."); setPreview(null); setName(""); }
    finally { setBusy(false); }
  }
  return <section className="mt-4 space-y-3 rounded border border-line p-4">
    <p>{t("Only combine these records if you have confirmed they represent the same person.")}</p>
    {!preview && <button disabled={busy} onClick={() => void review()} className="rounded bg-accent px-4 py-2 text-white">{t("Review merge: keep second client")}</button>}
    {preview && <>
      <h3 className="font-semibold">{t("Keep")}{" "}{preview.target.full_name}{t("; combine")}{" "}{preview.source.full_name}</h3>
      <p>{t("Keep contact details:")}{" "}{preview.target.email ?? t("No email")} · {preview.target.phone ?? t("No phone")} · {preview.target.role ?? t("No role")}</p>
      <p>{t("Original details archived:")}{" "}{preview.source.email ?? t("No email")} · {preview.source.phone ?? t("No phone")} · {preview.source.role ?? t("No role")}</p>
      <p>{t("Move")}{" "}{preview.moved.conversations}{" "}{t("conversations,")}{" "}{preview.moved.people}{" "}{t("person links,")}{" "}{preview.moved.client_facts}{" "}{t("facts, and")}{" "}{preview.moved.client_followup_actions}{" "}{t("follow-up events.")}</p>
      <p>{t("Saved AI client reviews will be archived because they describe the old histories. Recordings, notes, and tasks stay unchanged. The first client will disappear from the list. You can undo this in Recent merges & undo, provided the records have not changed afterward.")}</p>
      <label className="block">{t("Type")}{" "}{preview.target.full_name}{" "}{t("to confirm they are the same person")}<input disabled={busy} className="mt-2 block w-full rounded border border-line p-2" value={name} onChange={e => setName(e.target.value)} /></label>
      <button disabled={busy || name !== preview.target.full_name} onClick={() => void merge()} className="rounded bg-accent px-4 py-2 text-white disabled:opacity-50">{busy ? t("Combining…") : t("Confirm combine client records")}</button>
      <button disabled={busy} onClick={() => { setPreview(null); setName(""); }} className="ml-3 underline">{t("Cancel")}</button>
    </>}
    {error && <p role="alert">{t(error)}</p>}
  </section>;
}
