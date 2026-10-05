"use client";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { previewClientMerge, confirmClientMerge, type ClientMergePreview } from "@/lib/api";
export function MergeClients({ source, target, onMerged }: { source: string; target: string; onMerged: () => void }) {
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
    <p>Only combine these records if you have confirmed they represent the same person.</p>
    {!preview && <button disabled={busy} onClick={() => void review()} className="rounded bg-accent px-4 py-2 text-white">Review merge: keep second client</button>}
    {preview && <>
      <h3 className="font-semibold">Keep {preview.target.full_name}; combine {preview.source.full_name}</h3>
      <p>Keep contact details: {preview.target.email ?? "No email"} · {preview.target.phone ?? "No phone"} · {preview.target.role ?? "No role"}</p>
      <p>Original details archived: {preview.source.email ?? "No email"} · {preview.source.phone ?? "No phone"} · {preview.source.role ?? "No role"}</p>
      <p>Move {preview.moved.conversations} conversations, {preview.moved.people} person links, {preview.moved.client_facts} facts, and {preview.moved.client_followup_actions} follow-up events.</p>
      <p>Saved AI client reviews will be archived because they describe the old histories. Recordings, notes, and tasks stay unchanged. The first client will disappear from the list. You can undo this in Recent merges &amp; undo, provided the records have not changed afterward.</p>
      <label className="block">Type {preview.target.full_name} to confirm they are the same person<input disabled={busy} className="mt-2 block w-full rounded border border-line p-2" value={name} onChange={e => setName(e.target.value)} /></label>
      <button disabled={busy || name !== preview.target.full_name} onClick={() => void merge()} className="rounded bg-accent px-4 py-2 text-white disabled:opacity-50">{busy ? "Combining…" : "Confirm combine client records"}</button>
      <button disabled={busy} onClick={() => { setPreview(null); setName(""); }} className="ml-3 underline">Cancel</button>
    </>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
